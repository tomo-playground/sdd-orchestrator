"""Learn 노드 — 생성 결과를 Memory Store에 학습 데이터로 저장한다.

topic history, character stats, user global stats를 업데이트한다.
Phase 12-D: model_info, debate_groupthink_count, revision_accuracy 메트릭 추가.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from config import GEMINI_TEXT_MODEL, coerce_structure_id
from config import pipeline_logger as logger
from config_pipelines import CREATIVE_LEADER_MODEL, DIRECTOR_MODEL, REVIEW_MODEL, WRITER_MODEL
from services.agent.state import ScriptState
from services.agent.utils import topic_key


def _summarize_scenes(scenes: list[dict]) -> str:
    """씬 리스트를 간략한 요약 문자열로 변환한다."""
    if not scenes:
        return "No scenes"
    scripts = [s.get("script", "")[:50] for s in scenes[:3]]
    return f"{len(scenes)} scenes: " + " / ".join(scripts)


def _extract_quality_score(state: ScriptState) -> float | None:
    """Director checkpoint score를 추출한다."""
    return state.get("director_checkpoint_score")


def _extract_narrative_score(state: ScriptState) -> float | None:
    """Review result에서 narrative score overall을 추출한다."""
    review = state.get("review_result") or {}
    ns = review.get("narrative_score") or {}
    return ns.get("overall")


def _extract_hook_strategy(state: ScriptState) -> str | None:
    """Writer plan에서 hook_strategy를 추출한다."""
    plan = state.get("writer_plan") or {}
    return plan.get("hook_strategy")


def _count_groupthink(debate_log: list[dict]) -> int:
    """debate_log에서 groupthink_detected가 True인 라운드 수를 센다."""
    return sum(1 for entry in debate_log if entry.get("groupthink_detected"))


def _calc_revision_accuracy(state: ScriptState) -> float | None:
    """revision history에서 점수 개선율을 계산한다.

    첫 번째 revision 점수 대비 마지막 revision 점수의 개선 비율.
    revision이 없거나 점수가 없으면 None.
    """
    review = state.get("review_result") or {}
    ns = review.get("narrative_score") or {}
    final_score = ns.get("overall")

    checkpoint_score = state.get("director_checkpoint_score")
    revision_count = state.get("revision_count", 0)

    if revision_count == 0 or final_score is None or checkpoint_score is None:
        return None

    if checkpoint_score == 0:
        return None

    return round((final_score - checkpoint_score) / checkpoint_score, 3)


async def _update_topic(store: BaseStore, state: ScriptState, scenes: list[dict]) -> None:
    """토픽 히스토리에 이번 생성 결과를 추가한다 (최근 10건 유지)."""
    topic = state.get("topic", "")
    if not topic:
        return
    topic_ns = ("topic", topic_key(topic))
    existing = await store.asearch(topic_ns, limit=10)

    debate_log = state.get("debate_log") or []

    entry = {
        "summary": _summarize_scenes(scenes),
        "structure": coerce_structure_id(state.get("structure")),
        "scene_count": len(scenes),
        "created_at": datetime.now(UTC).isoformat(),
        "quality_score": _extract_quality_score(state),
        "narrative_score": _extract_narrative_score(state),
        "hook_strategy": _extract_hook_strategy(state),
        "revision_count": state.get("revision_count", 0),
        "skip_stages": state.get("skip_stages", []),
        "model_info": {
            "default": GEMINI_TEXT_MODEL,
            "director": DIRECTOR_MODEL,
            "writer": WRITER_MODEL,
            "review": REVIEW_MODEL,
            "critic": CREATIVE_LEADER_MODEL,
        },
        "debate_groupthink_count": _count_groupthink(debate_log),
        "revision_accuracy": _calc_revision_accuracy(state),
    }

    # 10건 초과 시 가장 오래된 항목 삭제
    if len(existing) >= 10:
        oldest = existing[-1]
        await store.adelete(topic_ns, oldest.key)

    await store.aput(topic_ns, str(uuid.uuid4()), entry)


async def _update_character(store: BaseStore, char_id: int | None) -> None:
    """캐릭터 생성 횟수를 증가시킨다."""
    if not char_id:
        return
    char_ns = ("character", str(char_id))
    existing = await store.asearch(char_ns, limit=1)

    if existing:
        data = existing[0].value
        data["generation_count"] = data.get("generation_count", 0) + 1
        data["last_used_at"] = datetime.now(UTC).isoformat()
        await store.aput(char_ns, existing[0].key, data)
    else:
        await store.aput(
            char_ns,
            str(uuid.uuid4()),
            {"generation_count": 1, "last_used_at": datetime.now(UTC).isoformat()},
        )


async def _update_user_stats(store: BaseStore) -> None:
    """전역 사용자 통계(총 생성 횟수)를 업데이트한다."""
    user_ns = ("user", "preferences")
    existing = await store.asearch(user_ns, limit=1)

    if existing:
        data = existing[0].value
        data["total_generations"] = data.get("total_generations", 0) + 1
        await store.aput(user_ns, existing[0].key, data)
    else:
        await store.aput(
            user_ns,
            str(uuid.uuid4()),
            {
                "total_generations": 1,
                "total_feedback": 0,
                "positive_count": 0,
                "positive_ratio": 0.0,
                "feedback_themes": [],
            },
        )


async def learn_node(state: ScriptState, config: RunnableConfig, *, store: BaseStore | None = None) -> dict:
    """생성 결과를 Memory Store에 저장한다."""
    if state.get("error"):
        logger.warning("[Learn] 에러 상태 전파 → %s", state.get("error"))
        return {"error": state.get("error"), "learn_result": {"stored": False, "reason": "error"}}

    if store is None:
        logger.info("[Learn] Store 미설정 — 학습 스킵")
        return {"learn_result": {"stored": False, "reason": "no_store"}}

    scenes = state.get("final_scenes") or []
    if not scenes:
        logger.info("[Learn] final_scenes 없음 — 학습 스킵")
        return {"learn_result": {"stored": False, "reason": "no_scenes"}}

    try:
        await asyncio.gather(
            _update_topic(store, state, scenes),
            _update_character(store, state.get("character_id")),
            _update_character(store, state.get("character_b_id")),
            _update_user_stats(store),
        )

        logger.info("[Learn] 학습 데이터 저장 완료: %d scenes", len(scenes))
        return {"learn_result": {"stored": True, "scene_count": len(scenes)}}
    except Exception as e:
        logger.error("[Learn] 저장 실패: %s", e)
        return {"learn_result": {"stored": False, "error": str(e)}}
