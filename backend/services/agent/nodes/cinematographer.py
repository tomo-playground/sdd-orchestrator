"""Cinematographer 노드 — 씬에 비주얼 디자인(Danbooru 태그, 카메라, 환경)을 추가한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState
from services.creative_qc import validate_visuals


def _load_character_tags(character_id: int | None) -> list[str] | None:
    """character_id로 캐릭터 비주얼 태그를 로드한다."""
    if not character_id:
        return None
    try:
        from database import get_db_session
        from models.character import Character

        with get_db_session() as db:
            char = db.query(Character).filter(Character.id == character_id).first()
            if not char:
                return None
            tags = [ct.tag.name for ct in char.tags if ct.tag]
            return tags or None
    except Exception as e:
        logger.warning("[Cinematographer] 캐릭터 태그 로드 실패: %s", e)
    return None


async def cinematographer_node(state: ScriptState) -> dict:
    """draft_scenes에 비주얼 디자인을 추가한다."""
    scenes = state.get("draft_scenes") or []
    character_tags = _load_character_tags(state.get("character_id"))

    template_vars = {"scenes": scenes, "character_tags": character_tags}
    try:
        result = await run_production_step(
            template_name="creative/cinematographer.j2",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_visuals(extracted),
            extract_key="scenes",
            step_name="cinematographer",
        )
        logger.info("[LangGraph] Cinematographer 완료: %d scenes", len(result.get("scenes", [])))
        return {"cinematographer_result": result}
    except Exception as e:
        logger.error("[LangGraph] Cinematographer 실패: %s", e)
        return {"error": f"Cinematographer failed: {e}"}
