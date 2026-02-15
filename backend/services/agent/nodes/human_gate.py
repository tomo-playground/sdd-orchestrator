"""Human Gate 노드 — interrupt() 기반 사용자 승인/수정 요청."""

from __future__ import annotations

from langgraph.types import interrupt

from services.agent.state import ScriptState


async def human_gate_node(state: ScriptState) -> dict:
    """사용자에게 승인/수정을 요청한다. interrupt()로 그래프를 일시 중지."""
    user_input = interrupt(
        {
            "type": "review_approval",
            "scenes": state.get("draft_scenes"),
            "review_result": state.get("review_result"),
            "scene_reasoning": state.get("scene_reasoning"),
        }
    )
    return {
        "human_action": user_input.get("action", "approve"),
        "human_feedback": user_input.get("feedback"),
    }
