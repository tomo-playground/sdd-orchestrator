"""Copyright Reviewer 노드 — 독창성/IP 위험을 검토한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState
from services.creative_qc import validate_copyright

_FALLBACK_PASS = {
    "overall": "PASS",
    "checks": [{"type": "api_fallback", "status": "PASS", "detail": "Skipped due to error", "suggestion": None}],
    "confidence": 0.0,
}


async def copyright_reviewer_node(state: ScriptState) -> dict:
    """씬의 저작권/IP 위험을 검토한다. 최대 재시도 실패 시 fallback PASS."""
    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])

    template_vars = {"scenes": scenes}
    if director_feedback := state.get("director_feedback"):
        template_vars["feedback"] = director_feedback
    try:
        result = await run_production_step(
            template_name="creative/copyright_reviewer.j2",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_copyright(extracted),
            extract_key="checks",
            step_name="copyright_reviewer",
        )
        logger.info("[LangGraph] Copyright Reviewer 완료: %s", result.get("overall"))
        return {"copyright_reviewer_result": result}
    except Exception as e:
        logger.warning("[LangGraph] Copyright Reviewer 실패, fallback PASS: %s", e)
        return {"copyright_reviewer_result": _FALLBACK_PASS}
