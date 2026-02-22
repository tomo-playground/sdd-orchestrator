"""Director 노드 — Production chain 결과를 ReAct Loop로 통합 검증한다.

Phase 10-A: Observe→Think→Act 루프 (최대 3 스텝)
Phase 10-C-2: Agent 간 메시지 기반 양방향 소통
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from config import logger
from config_pipelines import DIRECTOR_MODEL, LANGGRAPH_MAX_REACT_STEPS
from services.agent.llm_models import DirectorReActOutput, validate_with_model
from services.agent.messages import AgentMessage
from services.agent.nodes._agent_messaging import (
    extract_target_agent_from_decision,
    run_agent_with_message,
)
from services.agent.nodes._production_utils import run_production_step
from services.agent.observability import trace_llm_call
from services.agent.state import DirectorReActStep, ScriptState


async def director_node(state: ScriptState, config: RunnableConfig | None = None) -> dict:
    """Production 결과를 ReAct Loop로 통합 검증한다.

    Phase 10-A:
    - Observe→Think→Act 루프 (최대 LANGGRAPH_MAX_REACT_STEPS 스텝)
    - 각 스텝의 reasoning을 director_reasoning_steps에 기록
    - approve 판정 시 즉시 종료

    Phase 10-C-2:
    - revise 판정 시 타겟 에이전트에 메시지 전송
    - 에이전트 재실행 및 응답 수집
    - agent_messages에 메시지 로그 기록
    """
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "director"):
        return {"director_decision": "approve", "director_feedback": None}

    count = state.get("director_revision_count", 0)
    reasoning_steps: list[DirectorReActStep] = []
    messages: list[AgentMessage] = []

    production_results = {
        "cinematographer": state.get("cinematographer_result") or {},
        "tts_designer": state.get("tts_designer_result") or {},
        "sound_designer": state.get("sound_designer_result") or {},
        "copyright_reviewer": state.get("copyright_reviewer_result") or {},
    }

    final_decision = "approve"
    final_feedback = ""
    _react_validate_fn = lambda data: validate_with_model(DirectorReActOutput, data).model_dump()

    for step_num in range(1, LANGGRAPH_MAX_REACT_STEPS + 1):
        logger.info("[LangGraph] Director ReAct Step %d/%d", step_num, LANGGRAPH_MAX_REACT_STEPS)

        template_vars = {
            **production_results,
            "step_number": step_num,
            "max_steps": LANGGRAPH_MAX_REACT_STEPS,
            "previous_steps": reasoning_steps,
            "quality_criteria": (state.get("director_plan") or {}).get("quality_criteria", []),
            "visual_qc_result": state.get("visual_qc_result"),
        }

        try:
            async with trace_llm_call(
                name=f"director_react_step_{step_num}",
                input_text=f"Step {step_num}/{LANGGRAPH_MAX_REACT_STEPS}",
            ):
                result = await run_production_step(
                    template_name="creative/director.j2",
                    template_vars=template_vars,
                    validate_fn=_react_validate_fn,
                    extract_key="",
                    step_name=f"director_step_{step_num}",
                    model=DIRECTOR_MODEL,
                )

            react = DirectorReActOutput.model_validate(result)

            # ReAct 스텝 기록
            react_step: DirectorReActStep = {
                "step": step_num,
                "observe": react.observe,
                "think": react.think,
                "act": react.act,
            }
            reasoning_steps.append(react_step)

            logger.info(
                "[LangGraph] Director Step %d: act=%s, observe_len=%d, think_len=%d",
                step_num,
                react.act,
                len(react.observe),
                len(react.think),
            )

            # approve 판정 시 즉시 종료
            if react.act == "approve":
                final_decision = "approve"
                final_feedback = react.feedback or "모든 Production 요소가 조화롭게 작동합니다."
                logger.info("[LangGraph] Director 승인 (Step %d)", step_num)
                break

            # revise_* 판정 시 타겟 에이전트에 메시지 전송 (Phase 10-C-2)
            final_decision = react.act
            final_feedback = react.feedback

            target_agent = extract_target_agent_from_decision(react.act)
            if not target_agent and react.act.startswith("revise_"):
                # revise_script 등 production agent가 아닌 수정 요청 → 루프 종료 (routing이 처리)
                logger.info(
                    "[LangGraph] Director %s 판정 → routing으로 위임 (Step %d)",
                    react.act,
                    step_num,
                )
                break
            if target_agent:
                # Director → Agent 메시지 생성
                feedback_msg: AgentMessage = {
                    "sender": "director",
                    "recipient": target_agent,
                    "content": react.feedback,
                    "message_type": "feedback",
                }
                messages.append(feedback_msg)

                logger.info(
                    "[LangGraph] Director → %s: %s (Step %d)",
                    target_agent,
                    react.feedback[:50],
                    step_num,
                )

                # 타겟 에이전트 재실행
                try:
                    updated_result, response_msg = await run_agent_with_message(
                        target_agent=target_agent,
                        state=state,
                        message=feedback_msg,
                        config=config,
                    )

                    # 응답 메시지 기록
                    messages.append(response_msg)

                    # Production 결과 업데이트 (다음 스텝에서 사용)
                    production_results[target_agent] = updated_result

                    logger.info(
                        "[LangGraph] %s → Director: 응답 완료 (Step %d)",
                        target_agent,
                        step_num,
                    )

                except Exception as e:
                    logger.warning(
                        "[LangGraph] %s 재실행 실패 (Step %d): %s",
                        target_agent,
                        step_num,
                        e,
                    )

        except Exception as e:
            logger.warning("[LangGraph] Director ReAct Step %d 1차 실패: %s", step_num, e)
            try:
                async with trace_llm_call(
                    name=f"director_react_step_{step_num}_retry",
                    input_text=f"Retry Step {step_num}/{LANGGRAPH_MAX_REACT_STEPS}",
                ):
                    result = await run_production_step(
                        template_name="creative/director.j2",
                        template_vars=template_vars,
                        validate_fn=_react_validate_fn,
                        extract_key="",
                        step_name=f"director_step_{step_num}_retry",
                        model=DIRECTOR_MODEL,
                    )
                react = DirectorReActOutput.model_validate(result)
                react_step: DirectorReActStep = {
                    "step": step_num,
                    "observe": react.observe,
                    "think": react.think,
                    "act": react.act,
                }
                reasoning_steps.append(react_step)
                final_decision = react.act
                final_feedback = react.feedback or ""
                if react.act == "approve":
                    break
            except Exception as retry_err:
                logger.error("[LangGraph] Director Step %d 재시도 실패: %s", step_num, retry_err)
                final_decision = "error"
                final_feedback = f"Director Step {step_num} 평가 불가: {retry_err}"
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
        "agent_messages": messages,
    }
