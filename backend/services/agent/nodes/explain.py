"""Explain 노드 — Full 모드에서 파이프라인의 창작 결정을 설명한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState


async def explain_node(state: ScriptState) -> dict:
    """Production 결과를 분석하여 창작 결정 설명을 생성한다."""
    template_vars = {
        "final_scenes": state.get("final_scenes") or [],
        "cinematographer_result": state.get("cinematographer_result") or {},
        "tts_designer_result": state.get("tts_designer_result") or {},
        "sound_designer_result": state.get("sound_designer_result") or {},
        "copyright_reviewer_result": state.get("copyright_reviewer_result") or {},
        "director_decision": state.get("director_decision"),
        "director_feedback": state.get("director_feedback"),
        "scene_reasoning": state.get("scene_reasoning") or [],
    }
    try:
        result = await run_production_step(
            template_name="creative/explain.j2",
            template_vars=template_vars,
            validate_fn=lambda extracted: {"ok": bool(extracted), "issues": [], "checks": {}},
            extract_key="explanation",
            step_name="explain",
        )
        logger.info("[LangGraph] Explain 완료")
        return {"explanation_result": result}
    except Exception as e:
        logger.warning("[LangGraph] Explain 실패 (파이프라인 계속): %s", e)
        return {"explanation_result": None}
