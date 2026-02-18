"""Director 노드 — Production chain 결과를 ReAct Loop로 통합 검증한다.

Phase 10-A: Observe→Think→Act 루프 (최대 3 스텝)
"""

from __future__ import annotations

from config import logger
from config_pipelines import LANGGRAPH_MAX_REACT_STEPS
from services.agent.nodes._production_utils import run_production_step
from services.agent.observability import trace_llm_call
from services.agent.state import DirectorReActStep, ScriptState

_VALID_DECISIONS = frozenset(
    {
        "approve",
        "revise_cinematographer",
        "revise_tts",
        "revise_sound",
        "revise_script",
    }
)


def _validate_director_react(result: str | dict | list) -> dict:
    """Director ReAct 응답을 검증한다.

    Phase 10-A: observe, think, act 필드가 모두 존재하는지 확인.
    """
    if not isinstance(result, dict):
        return {"ok": False, "issues": ["Response must be a JSON object"], "checks": {}}

    required_fields = ["observe", "think", "act"]
    missing = [field for field in required_fields if field not in result]
    if missing:
        return {
            "ok": False,
            "issues": [f"Missing required fields: {', '.join(missing)}"],
            "checks": {},
        }

    act = result.get("act", "")
    if act not in _VALID_DECISIONS:
        return {"ok": False, "issues": [f"Invalid act decision: {act}"], "checks": {}}

    # feedback는 revise_* 시에만 필수
    if act != "approve" and not result.get("feedback"):
        return {"ok": False, "issues": ["feedback required for revise_* actions"], "checks": {}}

    return {"ok": True, "issues": [], "checks": {}}


async def director_node(state: ScriptState) -> dict:
    """Production 결과를 ReAct Loop로 통합 검증한다.

    Phase 10-A:
    - Observe→Think→Act 루프 (최대 LANGGRAPH_MAX_REACT_STEPS 스텝)
    - 각 스텝의 reasoning을 director_reasoning_steps에 기록
    - approve 판정 시 즉시 종료
    """
    count = state.get("director_revision_count", 0)
    reasoning_steps: list[DirectorReActStep] = []

    production_results = {
        "cinematographer": state.get("cinematographer_result") or {},
        "tts_designer": state.get("tts_designer_result") or {},
        "sound_designer": state.get("sound_designer_result") or {},
        "copyright_reviewer": state.get("copyright_reviewer_result") or {},
    }

    final_decision = "approve"
    final_feedback = ""

    for step_num in range(1, LANGGRAPH_MAX_REACT_STEPS + 1):
        logger.info("[LangGraph] Director ReAct Step %d/%d", step_num, LANGGRAPH_MAX_REACT_STEPS)

        template_vars = {
            **production_results,
            "step_number": step_num,
            "max_steps": LANGGRAPH_MAX_REACT_STEPS,
            "previous_steps": reasoning_steps,
        }

        try:
            async with trace_llm_call(
                name=f"director_react_step_{step_num}",
                input_text=f"Step {step_num}/{LANGGRAPH_MAX_REACT_STEPS}",
            ):
                result = await run_production_step(
                    template_name="creative/director.j2",
                    template_vars=template_vars,
                    validate_fn=_validate_director_react,
                    extract_key="",  # 빈 문자열 = 전체 dict 검증
                    step_name=f"director_step_{step_num}",
                )

            # ReAct 스텝 기록
            react_step: DirectorReActStep = {
                "step": step_num,
                "observe": result.get("observe", ""),
                "think": result.get("think", ""),
                "act": result.get("act", "approve"),
            }
            reasoning_steps.append(react_step)

            decision = result.get("act", "approve")
            feedback = result.get("feedback", "")

            logger.info(
                "[LangGraph] Director Step %d: act=%s, observe_len=%d, think_len=%d",
                step_num,
                decision,
                len(react_step["observe"]),
                len(react_step["think"]),
            )

            # approve 판정 시 즉시 종료
            if decision == "approve":
                final_decision = "approve"
                final_feedback = feedback or "모든 Production 요소가 조화롭게 작동합니다."
                logger.info("[LangGraph] Director 승인 (Step %d)", step_num)
                break

            # revise_* 판정 시 다음 스텝 계속
            final_decision = decision
            final_feedback = feedback

        except Exception as e:
            logger.warning("[LangGraph] Director ReAct Step %d 실패: %s", step_num, e)
            # 에러 시 해당 스텝까지의 reasoning은 보존하고 approve fallback
            final_decision = "approve"
            final_feedback = f"Director Step {step_num} 평가 실패, 자동 승인: {e}"
            break

    # 최대 스텝 도달 시에도 마지막 판정 유지
    if len(reasoning_steps) == LANGGRAPH_MAX_REACT_STEPS and final_decision != "approve":
        logger.warning(
            "[LangGraph] Director 최대 스텝 도달 (decision=%s), 마지막 판정 유지",
            final_decision,
        )

    logger.info(
        "[LangGraph] Director 완료: %d steps, final_decision=%s",
        len(reasoning_steps),
        final_decision,
    )

    return {
        "director_decision": final_decision,
        "director_feedback": final_feedback,
        "director_revision_count": count + 1,
        "director_reasoning_steps": reasoning_steps,
    }
