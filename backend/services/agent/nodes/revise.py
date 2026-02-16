"""Revise 노드 — Review 에러를 규칙 기반 또는 재생성으로 수정한다.

DD-4: 단순 오류(duration <= 0, 빈 필드)는 직접 수정, 복잡한 오류는 재생성.
"""

from __future__ import annotations

import re

from config import LANGGRAPH_MAX_REVISIONS, SCENE_DEFAULT_DURATION, logger
from database import get_db_session
from schemas import StoryboardRequest
from services.agent.state import ScriptState
from services.script.gemini_generator import generate_script

_DURATION_RE = re.compile(r"씬 (\d+): duration이 0 이하")
_FIELD_RE = re.compile(r"씬 (\d+): 필수 필드 '(script|image_prompt)' 누락")


def _try_rule_fix(scenes: list[dict], errors: list[str]) -> bool:
    """규칙 기반 수정을 시도한다. 모든 에러를 처리하면 True."""
    unresolved = 0
    for err in errors:
        if m := _DURATION_RE.search(err):
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(scenes):
                scenes[idx]["duration"] = SCENE_DEFAULT_DURATION
        elif m := _FIELD_RE.search(err):
            idx, field = int(m.group(1)) - 1, m.group(2)
            if 0 <= idx < len(scenes) and not scenes[idx].get(field):
                scenes[idx][field] = "(placeholder)" if field == "script" else "1girl, solo"
        else:
            unresolved += 1
    return unresolved == 0


def _build_feedback(state: ScriptState) -> str:
    """human_feedback, revision_feedback, review errors를 결합."""
    parts: list[str] = []
    if fb := state.get("human_feedback"):
        parts.append(f"[사용자 피드백] {fb}")
    if rf := state.get("revision_feedback"):
        parts.append(f"[수정 지시] {rf}")
    if df := state.get("director_feedback"):
        parts.append(f"[디렉터 피드백] {df}")
    review = state.get("review_result") or {}
    if errs := review.get("errors"):
        parts.append(f"[검증 오류] {'; '.join(errs)}")
    if ns := review.get("narrative_score"):
        if ns_fb := ns.get("feedback"):
            parts.append(f"[서사 품질 피드백] {ns_fb}")
    return "\n".join(parts)


def _make_request(state: ScriptState, desc: str) -> StoryboardRequest:
    """state에서 StoryboardRequest를 생성한다."""
    return StoryboardRequest(
        topic=state["topic"],
        description=desc,
        duration=state.get("duration", 10),
        style=state.get("style", "Anime"),
        language=state.get("language", "Korean"),
        structure=state.get("structure", "Monologue"),
        actor_a_gender=state.get("actor_a_gender", "female"),
        character_id=state.get("character_id"),
        character_b_id=state.get("character_b_id"),
        group_id=state.get("group_id"),
    )


async def revise_node(state: ScriptState) -> dict:
    """Review 에러를 수정한다. 단순 오류는 직접, 복잡 오류는 재생성."""
    count = state.get("revision_count", 0)
    if count >= LANGGRAPH_MAX_REVISIONS:
        logger.warning("[LangGraph] Revise 최대 횟수 도달 (%d)", count)
        return {"revision_count": count}

    scenes = [s.copy() for s in (state.get("draft_scenes") or [])]
    errors = (state.get("review_result") or {}).get("errors", [])

    if errors and _try_rule_fix(scenes, errors):
        logger.info("[LangGraph] Revise 규칙 수정 완료 (revision=%d)", count + 1)
        return {"draft_scenes": scenes, "revision_count": count + 1}

    # 복잡 오류: 피드백 주입 후 재생성
    feedback = _build_feedback(state)
    desc = state.get("description", "")
    desc = f"{desc}\n\n--- 수정 요청 ---\n{feedback}" if desc and feedback else (feedback or desc)

    with get_db_session() as db:
        try:
            result = await generate_script(_make_request(state, desc), db)
            logger.info("[LangGraph] Revise 재생성 완료 (revision=%d)", count + 1)
            return {
                "draft_scenes": result.get("scenes"),
                "draft_character_id": result.get("character_id"),
                "draft_character_b_id": result.get("character_b_id"),
                "revision_count": count + 1,
            }
        except Exception as e:
            logger.error("[LangGraph] Revise 재생성 실패: %s", e)
            return {"error": str(e), "revision_count": count + 1}
