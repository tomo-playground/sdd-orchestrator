"""Writer 노드 — 기존 generate_script를 래핑하여 초안을 생성한다."""

from __future__ import annotations

from config import logger
from database import get_db_session
from schemas import StoryboardRequest
from services.agent.state import ScriptState
from services.script.gemini_generator import generate_script


def _extract_reasoning(scenes: list[dict]) -> list[dict]:
    """각 씬에서 reasoning 필드를 추출한다. 없으면 빈 리스트."""
    reasoning = []
    for scene in scenes:
        r = scene.pop("reasoning", None)
        if isinstance(r, dict):
            reasoning.append(r)
        else:
            reasoning.append({})
    return reasoning


async def writer_node(state: ScriptState) -> dict:
    """StoryboardRequest를 생성하고 기존 generate_script를 호출한다."""
    # research_brief가 있으면 description에 컨텍스트 추가
    desc = state.get("description", "")
    research_brief = state.get("research_brief")
    if research_brief:
        desc = f"{desc}\n\n[참고 정보]\n{research_brief}".strip()

    # revision_feedback가 있으면 description에 주입
    feedback = state.get("revision_feedback")
    if feedback:
        desc = f"{desc}\n\n[수정 요청] {feedback}".strip()

    request = StoryboardRequest(
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

    with get_db_session() as db:
        try:
            result = await generate_script(request, db)
            scenes = result.get("scenes", [])
            scene_reasoning = _extract_reasoning(scenes)
            logger.info("[LangGraph] Writer 노드 완료: %d scenes", len(scenes))
            return {
                "draft_scenes": scenes,
                "draft_character_id": result.get("character_id"),
                "draft_character_b_id": result.get("character_b_id"),
                "scene_reasoning": scene_reasoning or None,
            }
        except Exception as e:
            logger.error("[LangGraph] Writer 노드 실패: %s", e)
            return {"error": str(e)}
