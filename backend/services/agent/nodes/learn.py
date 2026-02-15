"""Learn 노드 — 생성 결과를 Memory Store에 학습 데이터로 저장한다.

topic history, character stats, user global stats를 업데이트한다.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from config import logger
from services.agent.state import ScriptState


def _topic_key(topic: str) -> str:
    """토픽 문자열을 12자리 MD5 해시로 변환한다."""
    return hashlib.md5(topic.encode()).hexdigest()[:12]


def _summarize_scenes(scenes: list[dict]) -> str:
    """씬 리스트를 간략한 요약 문자열로 변환한다."""
    if not scenes:
        return "No scenes"
    scripts = [s.get("script", "")[:50] for s in scenes[:3]]
    return f"{len(scenes)} scenes: " + " / ".join(scripts)


async def _update_topic(store: BaseStore, state: ScriptState, scenes: list[dict]) -> None:
    """토픽 히스토리에 이번 생성 결과를 추가한다 (최근 10건 유지)."""
    topic = state.get("topic", "")
    if not topic:
        return
    topic_ns = ("topic", _topic_key(topic))
    existing = await store.asearch(topic_ns, limit=10)

    entry = {
        "summary": _summarize_scenes(scenes),
        "structure": state.get("structure", ""),
        "scene_count": len(scenes),
        "created_at": datetime.now(UTC).isoformat(),
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


async def learn_node(state: ScriptState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """생성 결과를 Memory Store에 저장한다."""
    scenes = state.get("final_scenes") or []
    if not scenes:
        logger.info("[Learn] final_scenes 없음 — 학습 스킵")
        return {"learn_result": {"stored": False, "reason": "no_scenes"}}

    try:
        await _update_topic(store, state, scenes)
        await _update_character(store, state.get("character_id"))
        await _update_user_stats(store)

        logger.info("[Learn] 학습 데이터 저장 완료: %d scenes", len(scenes))
        return {"learn_result": {"stored": True, "scene_count": len(scenes)}}
    except Exception as e:
        logger.error("[Learn] 저장 실패: %s", e)
        return {"learn_result": {"stored": False, "error": str(e)}}
