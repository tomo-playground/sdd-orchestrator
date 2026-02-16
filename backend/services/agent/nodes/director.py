"""Director 노드 — Production chain 결과를 통합 검증한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState

_VALID_DECISIONS = frozenset(
    {
        "approve",
        "revise_cinematographer",
        "revise_tts",
        "revise_sound",
        "revise_script",
    }
)


def _validate_director(result: str | dict | list) -> dict:
    """Director 응답의 decision 필드를 검증한다.

    run_production_step 내부에서 extract_key="decision"으로 추출된 문자열이 전달되거나,
    dict 형태로 전달될 수 있다.
    """
    if isinstance(result, str):
        decision = result
    elif isinstance(result, dict):
        decision = result.get("decision", "")
    else:
        return {"ok": False, "issues": ["Unexpected type"], "checks": {}}
    if decision not in _VALID_DECISIONS:
        return {"ok": False, "issues": [f"Invalid decision: {decision}"], "checks": {}}
    return {"ok": True, "issues": [], "checks": {}}


async def director_node(state: ScriptState) -> dict:
    """Production 결과를 통합 검증하고 다음 행동을 결정한다."""
    count = state.get("director_revision_count", 0)

    template_vars = {
        "cinematographer": state.get("cinematographer_result") or {},
        "tts_designer": state.get("tts_designer_result") or {},
        "sound_designer": state.get("sound_designer_result") or {},
        "copyright_reviewer": state.get("copyright_reviewer_result") or {},
    }

    try:
        result = await run_production_step(
            template_name="creative/director.j2",
            template_vars=template_vars,
            validate_fn=_validate_director,
            extract_key="decision",
            step_name="director",
        )
        decision = result.get("decision", "approve")
        feedback = result.get("feedback", "")
        logger.info("[LangGraph] Director 완료: decision=%s", decision)
        return {
            "director_decision": decision,
            "director_feedback": feedback,
            "director_revision_count": count + 1,
        }
    except Exception as e:
        logger.warning("[LangGraph] Director 실패, approve fallback: %s", e)
        return {
            "director_decision": "approve",
            "director_feedback": f"Director 평가 실패, 자동 승인: {e}",
            "director_revision_count": count + 1,
        }
