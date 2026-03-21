"""Concept Gate 노드 — critic과 writer 사이에서 컨셉 선택을 중재한다.

Full Auto 모드: pass-through (interrupt 없이 critic 선택 유지)
Creator 모드: interrupt()로 사용자에게 3개 컨셉을 제시, 선택 후 writer 진행
Quick 모드: 이 노드에 도달하지 않음 (research/critic 스킵)
"""

from __future__ import annotations

from langgraph.types import interrupt

from config import logger
from config_pipelines import LANGGRAPH_MAX_CONCEPT_REGEN
from services.agent.nodes._skip_guard import should_skip
from services.agent.state import ScriptState


async def concept_gate_node(state: ScriptState) -> dict:
    """컨셉 선택 게이트. auto_approve면 pass-through, 아니면 사용자 선택 대기."""
    mode = state.get("interaction_mode", "guided")
    if should_skip(state, "concept_gate"):
        return {"concept_action": "select"}

    if mode == "auto" or state.get("auto_approve"):
        logger.debug("[LangGraph:ConceptGate] mode=%s → auto-select (skip interrupt)", mode)
        return {"concept_action": "select"}

    critic_result = state.get("critic_result") or {}
    candidates_count = len(critic_result.get("candidates", []))
    logger.info(
        "[LangGraph:ConceptGate] interrupt 발행 — 사용자 컨셉 선택 대기 (candidates=%d)",
        candidates_count,
    )
    user_input = interrupt(
        {
            "type": "concept_selection",
            "candidates": critic_result.get("candidates", []),
            "selected_concept": critic_result.get("selected_concept"),
            "evaluation": critic_result.get("evaluation"),
        }
    )

    action = user_input.get("action", "select")
    logger.info("[LangGraph:ConceptGate] 사용자 응답 수신: action=%s", action)
    return _process_action(action, user_input, critic_result, state)


def _process_action(action: str, user_input: dict, critic_result: dict, state: ScriptState) -> dict:
    """action에 따라 분기 처리한다."""
    if action == "regenerate":
        return _handle_regenerate(state)
    if action == "custom_concept":
        return _handle_custom_concept(user_input, critic_result)
    return _handle_select(user_input, critic_result)


def _handle_regenerate(state: ScriptState) -> dict:
    """컨셉 재생성 요청. 최대 횟수 초과 시 첫 번째 컨셉으로 강제 선택."""
    count = state.get("concept_regen_count", 0) + 1
    if count > LANGGRAPH_MAX_CONCEPT_REGEN:
        logger.info(
            "[LangGraph:ConceptGate] regen 횟수 초과 (%d > %d) → 강제 select",
            count,
            LANGGRAPH_MAX_CONCEPT_REGEN,
        )
        return {"concept_action": "select", "concept_regen_count": count}
    return {
        "critic_result": None,
        "concept_action": "regenerate",
        "concept_regen_count": count,
    }


def _handle_custom_concept(user_input: dict, critic_result: dict) -> dict:
    """사용자 직접 입력 컨셉을 synthetic concept로 주입."""
    custom = user_input.get("custom_concept", {})
    updated = dict(critic_result)
    updated["selected_concept"] = custom
    return {"critic_result": updated, "concept_action": "select"}


def _handle_select(user_input: dict, critic_result: dict) -> dict:
    """기존 컨셉 선택 로직."""
    concept_id = user_input.get("concept_id", 0)
    candidates = critic_result.get("candidates", [])
    in_range = 0 <= concept_id < len(candidates)
    selected = candidates[concept_id] if in_range else (candidates[0] if candidates else {})
    updated = dict(critic_result)
    updated["selected_concept"] = selected
    return {"critic_result": updated, "concept_action": "select"}
