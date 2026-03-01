"""Human Gate 노드 — interrupt() 기반 사용자 승인/수정 요청."""

from __future__ import annotations

from langgraph.types import interrupt

from services.agent.state import ScriptState


async def human_gate_node(state: ScriptState) -> dict:
    """사용자에게 승인/수정을 요청한다. interrupt()로 그래프를 일시 중지."""
    mode = state.get("interaction_mode", "guided")
    if mode != "hands_on":
        return {"human_action": "approve"}

    user_input = interrupt(
        {
            "type": "review_approval",
            "scenes": state.get("draft_scenes"),
            "review_result": state.get("review_result"),
            "scene_reasoning": state.get("scene_reasoning"),
            "director_decision": state.get("director_decision"),
            "director_feedback": state.get("director_feedback"),
            "director_reasoning_steps": state.get("director_reasoning_steps"),
        }
    )
    action = user_input.get("action", "approve")
    result: dict = {
        "human_action": action,
        "human_feedback": user_input.get("feedback"),
    }
    # 사용자 수정 요청 시 자동 revision 카운터를 리셋하여
    # 빠른 수정이 차단되지 않도록 한다
    if action == "revise":
        result["revision_count"] = 0
    return result
