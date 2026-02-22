"""Director Plan 노드 — 초기 목표 수립 + 실행 계획.

Full 모드에서 START 직후 실행되어 creative_goal, target_emotion,
quality_criteria 등을 설정한다. 후속 노드(Writer, Checkpoint, Director)가 참조.
"""

from __future__ import annotations

from config import logger
from services.agent.llm_models import DirectorPlanOutput, validate_with_model
from services.agent.nodes._production_utils import run_production_step
from services.agent.nodes._skip_guard import should_skip
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState


async def director_plan_node(state: ScriptState, config=None) -> dict:
    """Creative Director의 초기 목표 수립 노드."""
    if should_skip(state, "director_plan"):
        return {"director_plan": None}

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
                validate_fn=lambda data: validate_with_model(DirectorPlanOutput, data).model_dump(),
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
