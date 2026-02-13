"""Draft 노드 — 기존 generate_script를 래핑하여 초안을 생성한다."""

from __future__ import annotations

from config import logger
from database import SessionLocal
from schemas import StoryboardRequest
from services.agent.state import ScriptState
from services.script.gemini_generator import generate_script


async def draft_node(state: ScriptState) -> dict:
    """StoryboardRequest를 생성하고 기존 generate_script를 호출한다."""
    request = StoryboardRequest(
        topic=state["topic"],
        description=state.get("description", ""),
        duration=state.get("duration", 10),
        style=state.get("style", "Anime"),
        language=state.get("language", "Korean"),
        structure=state.get("structure", "Monologue"),
        actor_a_gender=state.get("actor_a_gender", "female"),
        character_id=state.get("character_id"),
        character_b_id=state.get("character_b_id"),
        group_id=state.get("group_id"),
    )

    db = SessionLocal()
    try:
        result = await generate_script(request, db)
        logger.info("[LangGraph] Draft 노드 완료: %d scenes", len(result.get("scenes", [])))
        return {
            "draft_scenes": result.get("scenes"),
            "draft_character_id": result.get("character_id"),
            "draft_character_b_id": result.get("character_b_id"),
        }
    except Exception as e:
        logger.error("[LangGraph] Draft 노드 실패: %s", e)
        return {"error": str(e)}
    finally:
        db.close()
