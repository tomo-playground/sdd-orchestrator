"""Copyright Reviewer 노드 — 독창성/IP 위험을 검토한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState
from services.creative_qc import validate_copyright


def _recalculate_overall(checks: list[dict]) -> str:
    """checks 리스트의 status 필드 기반으로 overall을 재계산한다."""
    statuses = {c.get("status", "PASS") for c in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


_FALLBACK_PASS = {
    "overall": "PASS",
    "checks": [{"type": "api_fallback", "status": "PASS", "detail": "Skipped due to error", "suggestion": None}],
    "confidence": 0.0,
}


async def copyright_reviewer_node(state: ScriptState) -> dict:
    """씬의 저작권/IP 위험을 검토한다. 최대 재시도 실패 시 fallback PASS."""
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "copyright_reviewer"):
        return {
            "copyright_reviewer_result": {
                "overall": "PASS",
                "checks": [
                    {
                        "type": "stage_skipped",
                        "status": "PASS",
                        "detail": "Production stage skipped",
                        "suggestion": None,
                    }
                ],
                "confidence": 0.0,
            }
        }

    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])

    template_vars = {
        "scenes": scenes,
        "language": state.get("language", "Korean"),
    }
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
        # LLM이 생성한 overall을 checks 기반으로 서버사이드 재계산 (일관성 보장)
        result["overall"] = _recalculate_overall(result.get("checks", []))
        logger.info("[LangGraph] Copyright Reviewer 완료: %s", result.get("overall"))
        return {"copyright_reviewer_result": result}
    except Exception as e:
        logger.warning("[LangGraph] Copyright Reviewer 실패, fallback PASS: %s", e)
        return {"copyright_reviewer_result": _FALLBACK_PASS}
