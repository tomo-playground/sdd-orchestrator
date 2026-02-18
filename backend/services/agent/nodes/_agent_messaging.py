"""Agent 메시지 라우팅 유틸리티 (Phase 10-C-2).

Director와 Production Agent 간 양방향 메시지 전달.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from config import logger
from services.agent.messages import AgentMessage
from services.agent.state import ScriptState


async def run_agent_with_message(
    target_agent: str,
    state: ScriptState,
    message: AgentMessage,
    config: RunnableConfig | None = None,
) -> tuple[dict, AgentMessage]:
    """타겟 에이전트를 메시지와 함께 실행하고 응답을 받는다.

    Args:
        target_agent: 타겟 에이전트명 ("cinematographer", "tts_designer", 등)
        state: 현재 ScriptState
        message: 발신 메시지 (Director → Agent)
        config: LangGraph config (optional)

    Returns:
        (updated_result, response_message) 튜플
        - updated_result: 에이전트가 재생성한 결과 dict
        - response_message: 에이전트의 응답 메시지

    Raises:
        ValueError: 지원하지 않는 target_agent
    """
    logger.info(
        "[AgentMessaging] run_agent_with_message: target=%s, message_type=%s",
        target_agent,
        message.get("message_type"),
    )

    # 메시지를 state에 주입 (에이전트가 읽을 수 있도록)
    state_with_message = dict(state)
    state_with_message["director_feedback"] = message.get("content", "")

    # 타겟 에이전트 실행
    if target_agent == "cinematographer":
        from .cinematographer import cinematographer_node

        result = await cinematographer_node(state_with_message, config or {})
        updated_result = result.get("cinematographer_result") or {}

    elif target_agent == "tts_designer":
        from .tts_designer import tts_designer_node

        result = await tts_designer_node(state_with_message)
        updated_result = result.get("tts_designer_result") or {}

    elif target_agent == "sound_designer":
        from .sound_designer import sound_designer_node

        result = await sound_designer_node(state_with_message)
        updated_result = result.get("sound_designer_result") or {}

    elif target_agent == "copyright_reviewer":
        from .copyright_reviewer import copyright_reviewer_node

        result = await copyright_reviewer_node(state_with_message)
        updated_result = result.get("copyright_reviewer_result") or {}

    else:
        raise ValueError(f"Unsupported target agent: {target_agent}")

    # 응답 메시지 생성
    response: AgentMessage = {
        "sender": target_agent,
        "recipient": message.get("sender", "director"),
        "content": f"{target_agent} 피드백 반영 완료",
        "message_type": "approval",
        "metadata": {"result": updated_result},
    }

    logger.info("[AgentMessaging] Agent %s 응답 완료", target_agent)

    return updated_result, response


def extract_target_agent_from_decision(decision: str) -> str | None:
    """Director decision에서 타겟 에이전트명을 추출한다.

    Args:
        decision: Director의 act 결정 (예: "revise_cinematographer")

    Returns:
        타겟 에이전트명 (예: "cinematographer") 또는 None (approve 시)
    """
    if decision == "approve":
        return None

    # "revise_cinematographer" → "cinematographer"
    # "revise_tts" → "tts_designer"
    # "revise_sound" → "sound_designer"
    # "revise_script" → None (script는 writer로 돌아가므로 production agent 아님)

    mapping = {
        "revise_cinematographer": "cinematographer",
        "revise_tts": "tts_designer",
        "revise_sound": "sound_designer",
    }

    return mapping.get(decision)
