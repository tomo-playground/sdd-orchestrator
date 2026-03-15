"""Director Plan Gate 노드 — director_plan 이후 사용자 플랜 검토를 중재한다.

Auto 모드: pass-through (interrupt 없이 즉시 진행)
Guided 모드: interrupt()로 사용자에게 플랜을 제시, 승인/수정 후 진행
Hands-on 모드: Guided와 동일
"""

from __future__ import annotations

from langgraph.types import interrupt

from services.agent.nodes._skip_guard import should_skip
from services.agent.state import ScriptState


async def director_plan_gate_node(state: ScriptState) -> dict:
    """플랜 검토 게이트. auto면 pass-through, 아니면 사용자 검토 대기."""
    if should_skip(state, "director_plan_gate"):
        return {"plan_action": "proceed"}

    mode = state.get("interaction_mode", "guided")
    if mode == "auto" or state.get("auto_approve"):
        return {"plan_action": "proceed"}

    director_plan = state.get("director_plan") or {}
    skip_stages = state.get("skip_stages") or []

    user_input = interrupt(
        {
            "type": "plan_review",
            "director_plan": director_plan,
            "skip_stages": skip_stages,
        }
    )

    action = user_input.get("action", "proceed")
    if action == "revise_plan":
        return _handle_revise(state, user_input)
    return {"plan_action": "proceed"}


def _handle_revise(state: ScriptState, user_input: dict) -> dict:
    """플랜 수정 요청. 최대 2회 초과 시 강제 진행."""
    count = state.get("plan_revision_count", 0) + 1
    if count > 2:
        return {"plan_action": "proceed", "plan_revision_count": count}

    feedback = user_input.get("feedback", "")
    # description에 누적하지 않고 revision_feedback 필드에 저장 (writer_node가 별도로 소비)
    return {
        "plan_action": "revise",
        "revision_feedback": feedback,
        "plan_revision_count": count,
    }


__all__ = ["director_plan_gate_node"]
