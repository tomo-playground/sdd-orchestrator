"""TTS Designer 노드 — 씬별 음성 디자인(감정, 톤, 페이싱)을 생성한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState
from services.creative_qc import validate_tts_design


async def tts_designer_node(state: ScriptState) -> dict:
    """cinematographer_result의 씬을 기반으로 TTS 디자인을 생성한다."""
    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])
    concept = state.get("critic_result") or {}

    template_vars = {"scenes": scenes, "concept": concept}
    try:
        result = await run_production_step(
            template_name="creative/tts_designer.j2",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_tts_design(extracted),
            extract_key="tts_designs",
            step_name="tts_designer",
        )
        logger.info("[LangGraph] TTS Designer 완료: %d designs", len(result.get("tts_designs", [])))
        return {"tts_designer_result": result}
    except Exception as e:
        logger.error("[LangGraph] TTS Designer 실패: %s", e)
        return {"error": f"TTS Designer failed: {e}"}
