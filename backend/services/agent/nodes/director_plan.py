"""Director Plan 노드 — 초기 목표 수립 + 실행 계획.

Full 모드에서 START 직후 실행되어 creative_goal, target_emotion,
quality_criteria 등을 설정한다. 후속 노드(Writer, Checkpoint, Director)가 참조.
"""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState


def _validate_director_plan(result: dict | list | str) -> dict:
    """Director Plan 응답 검증: creative_goal, target_emotion, quality_criteria 필수."""
    if not isinstance(result, dict):
        return {"ok": False, "issues": ["Response must be a JSON object"], "checks": {}}

    missing = []
    if not result.get("creative_goal"):
        missing.append("creative_goal")
    if not result.get("target_emotion"):
        missing.append("target_emotion")
    criteria = result.get("quality_criteria")
    if not criteria or not isinstance(criteria, list) or len(criteria) < 1:
        missing.append("quality_criteria (list, 1개 이상)")

    if missing:
        return {"ok": False, "issues": [f"Missing: {', '.join(missing)}"], "checks": {}}
    return {"ok": True, "issues": [], "checks": {}}


async def director_plan_node(state: ScriptState, config=None) -> dict:
    """Creative Director의 초기 목표 수립 노드."""
    template_vars = {
        "topic": state.get("topic", ""),
        "description": state.get("description", ""),
        "duration": state.get("duration", 30),
        "style": state.get("style", ""),
        "language": state.get("language", "ko"),
        "structure": state.get("structure", ""),
        "references": state.get("references") or [],
    }

    try:
        async with trace_llm_call(name="director_plan", input_text=template_vars.get("topic", "")):
            result = await run_production_step(
                template_name="creative/director_plan.j2",
                template_vars=template_vars,
                validate_fn=_validate_director_plan,
                extract_key="",
                step_name="director_plan",
            )

        plan = {
            "creative_goal": result.get("creative_goal", ""),
            "target_emotion": result.get("target_emotion", ""),
            "quality_criteria": result.get("quality_criteria", []),
            "risk_areas": result.get("risk_areas", []),
            "style_direction": result.get("style_direction", ""),
        }
        logger.info("[LangGraph] Director Plan 수립 완료: goal=%s", plan["creative_goal"][:50])
        return {"director_plan": plan}

    except Exception as e:
        logger.warning("[LangGraph] Director Plan 실패, graceful degradation: %s", e)
        return {"director_plan": None}
