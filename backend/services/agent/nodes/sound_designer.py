"""Sound Designer 노드 — BGM 방향성을 추천한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState
from services.creative_qc import validate_music


async def sound_designer_node(state: ScriptState) -> dict:
    """cinematographer_result의 씬을 기반으로 BGM 추천을 생성한다."""
    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])
    concept = state.get("critic_result") or {}
    duration = state.get("duration", 30)

    template_vars = {"scenes": scenes, "concept": concept, "duration": duration}
    try:
        result = await run_production_step(
            template_name="creative/sound_designer.j2",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_music(extracted),
            extract_key="recommendation",
            step_name="sound_designer",
        )
        logger.info("[LangGraph] Sound Designer 완료")
        return {"sound_designer_result": result}
    except Exception as e:
        logger.error("[LangGraph] Sound Designer 실패: %s", e)
        return {"error": f"Sound Designer failed: {e}"}
