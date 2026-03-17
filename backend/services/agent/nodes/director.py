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
from services.agent.prompt_builders import (
    build_previous_steps_block,
    build_quality_criteria_block,
    build_visual_qc_section,
    to_json,
)
from services.agent.state import DirectorReActStep, ScriptState

# Agent 이름 → State 키 매핑 (인라인 수정 결과 반영용)
_AGENT_STATE_KEY_MAP = {
    "cinematographer": "cinematographer_result",
    "tts_designer": "tts_designer_result",
    "sound_designer": "sound_designer_result",
    "copyright_reviewer": "copyright_reviewer_result",
}


def _react_validate_fn(data: dict) -> dict:
    return validate_with_model(DirectorReActOutput, data).model_dump()


async def director_node(state: ScriptState, config: RunnableConfig) -> dict:
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

    # 인라인 수정된 에이전트 추적 (BUG 1: 수정 결과를 State에 반영하기 위함)
    revised_agents: set[str] = set()

    final_decision = "approve"
    final_feedback = ""

    for step_num in range(1, LANGGRAPH_MAX_REACT_STEPS + 1):
        logger.info("[LangGraph] Director ReAct Step %d/%d", step_num, LANGGRAPH_MAX_REACT_STEPS)

        template_vars = {
            "cinematographer_json": to_json(production_results.get("cinematographer", {})),
            "tts_designer_json": to_json(production_results.get("tts_designer", {})),
            "sound_designer_json": to_json(production_results.get("sound_designer", {})),
            "copyright_reviewer_json": to_json(production_results.get("copyright_reviewer", {})),
            "step_number": str(step_num),
            "max_steps": str(LANGGRAPH_MAX_REACT_STEPS),
            "quality_criteria_block": build_quality_criteria_block(
                (state.get("director_plan") or {}).get("quality_criteria", []),
            ),
            "visual_qc_section": build_visual_qc_section(state.get("visual_qc_result")),
            "previous_steps_block": build_previous_steps_block(reasoning_steps),
        }

        try:
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
                "feedback": react.feedback or "",
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
                    revised_agents.add(target_agent)

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
                result = await run_production_step(
                    template_name="creative/director.j2",
                    template_vars=template_vars,
                    validate_fn=_react_validate_fn,
                    extract_key="",
                    step_name=f"director_step_{step_num}_retry",
                    model=DIRECTOR_MODEL,
                    )
                react = DirectorReActOutput.model_validate(result)
                react_step = {
                    "step": step_num,
                    "observe": react.observe,
                    "think": react.think,
                    "act": react.act,
                    "feedback": react.feedback or "",
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

    # revise 스텝이 한 번이라도 발생했을 때만 카운트 증가 (즉시 approve 시 증가 방지)
    had_revise_step = any(step.get("act", "approve") != "approve" for step in reasoning_steps)
    new_count = count + 1 if (had_revise_step or final_decision == "error") else count
    result_dict: dict = {
        "director_decision": final_decision,
        "director_feedback": final_feedback,
        "director_revision_count": new_count,
        "director_reasoning_steps": reasoning_steps,
        "agent_messages": messages,
    }
    for agent_name in revised_agents:
        state_key = _AGENT_STATE_KEY_MAP.get(agent_name)
        if state_key is None:
            logger.warning("[Director] 알 수 없는 에이전트명 '%s', state 업데이트 스킵", agent_name)
            continue
        result_dict[state_key] = production_results[agent_name]

    return result_dict
