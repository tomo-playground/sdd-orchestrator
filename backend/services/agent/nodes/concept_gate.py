"""Concept Gate 노드 — critic과 writer 사이에서 컨셉 선택을 중재한다.

Full Auto 모드: pass-through (interrupt 없이 critic 선택 유지)
Creator 모드: interrupt()로 사용자에게 3개 컨셉을 제시, 선택 후 writer 진행
Quick 모드: 이 노드에 도달하지 않음 (research/critic 스킵)
"""

from __future__ import annotations

from langgraph.types import interrupt

from services.agent.state import ScriptState


async def concept_gate_node(state: ScriptState) -> dict:
    """컨셉 선택 게이트. auto_approve면 pass-through, 아니면 사용자 선택 대기."""
    if state.get("auto_approve"):
        return {}

    critic_result = state.get("critic_result") or {}
    user_input = interrupt(
        {
            "type": "concept_selection",
            "candidates": critic_result.get("candidates", []),
            "selected_concept": critic_result.get("selected_concept"),
            "evaluation": critic_result.get("evaluation"),
        }
    )

    concept_id = user_input.get("concept_id", 0)
    candidates = critic_result.get("candidates", [])
    selected = candidates[concept_id] if 0 <= concept_id < len(candidates) else (candidates[0] if candidates else {})

    updated = dict(critic_result)
    updated["selected_concept"] = selected
    return {"critic_result": updated}
