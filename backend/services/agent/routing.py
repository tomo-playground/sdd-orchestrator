"""조건 분기 함수 — Graph 엣지에서 사용하는 라우팅 로직.

script_graph.py의 파일 크기를 줄이기 위해 분리.
"""

from __future__ import annotations

from config import LANGGRAPH_MAX_REVISIONS, logger
from config_pipelines import LANGGRAPH_MAX_DIRECTOR_REVISIONS
from services.agent.state import ScriptState

_DIRECTOR_DECISION_MAP: dict[str, str] = {
    "revise_cinematographer": "cinematographer",
    "revise_tts": "tts_designer",
    "revise_sound": "sound_designer",
    "revise_script": "revise",
}


def _has_error(state: ScriptState) -> bool:
    """에러 상태인지 확인."""
    return bool(state.get("error"))


def route_after_start(state: ScriptState) -> str:
    """START 이후: mode에 따라 research(full) 또는 writer(quick) 분기."""
    mode = state.get("mode", "quick")
    if mode == "full":
        return "research"
    return "writer"


def route_after_writer(state: ScriptState) -> str:
    """writer 이후: 에러 → finalize (short-circuit), 정상 → review."""
    if _has_error(state):
        logger.warning("[LangGraph] writer 에러, finalize로 short-circuit")
        return "finalize"
    return "review"


def route_after_review(state: ScriptState) -> str:
    """review 이후: passed → cinematographer(full)/finalize(quick), failed → revise.

    Quick → finalize 직행, Full → cinematographer (Production chain 시작).
    에러 상태이면 즉시 finalize로 short-circuit.
    """
    if _has_error(state):
        logger.warning("[LangGraph] review 진입 시 에러 발견, finalize로 short-circuit")
        return "finalize"

    result = state.get("review_result")
    passed = result.get("passed") if result else False

    # 실패했으나 revision 여유가 있으면 revise
    if not passed:
        count = state.get("revision_count", 0)
        if count < LANGGRAPH_MAX_REVISIONS:
            return "revise"
        logger.warning(
            "[LangGraph] 최대 revision 횟수(%d) 도달, 강제 통과",
            LANGGRAPH_MAX_REVISIONS,
        )

    # passed 또는 max_revision 도달 → Quick: finalize / Full: cinematographer
    mode = state.get("mode", "quick")
    if mode != "full":
        return "finalize"
    return "cinematographer"


def route_after_cinematographer(state: ScriptState) -> list[str] | str:
    """cinematographer 이후: 에러 → finalize, 정상 → 3개 병렬 fan-out."""
    if _has_error(state):
        return "finalize"
    return ["tts_designer", "sound_designer", "copyright_reviewer"]


def route_after_director(state: ScriptState) -> str:
    """Director 이후: approve → human_gate/finalize, revise → 해당 노드."""
    if _has_error(state):
        return "finalize"

    decision = state.get("director_decision", "approve")

    if decision == "approve":
        if state.get("auto_approve"):
            return "finalize"
        return "human_gate"

    # revision 횟수 체크 (최대 LANGGRAPH_MAX_DIRECTOR_REVISIONS)
    count = state.get("director_revision_count", 0)
    if count >= LANGGRAPH_MAX_DIRECTOR_REVISIONS:
        logger.warning("[LangGraph] Director revision 최대 횟수(%d) 도달, 강제 통과", count)
        return "human_gate"

    return _DIRECTOR_DECISION_MAP.get(decision, "human_gate")


def route_after_concept_gate(state: ScriptState) -> str:
    """Concept Gate 이후: regenerate → critic (재생성), 그 외 → writer."""
    if state.get("concept_action") == "regenerate":
        return "critic"
    return "writer"


def route_after_human_gate(state: ScriptState) -> str:
    """Human Gate 이후: approve → finalize, revise → revise."""
    action = state.get("human_action", "approve")
    if action == "revise":
        return "revise"
    return "finalize"


def route_after_finalize(state: ScriptState) -> str:
    """finalize 이후: Full → explain, Quick → learn."""
    if state.get("mode", "quick") == "full":
        return "explain"
    return "learn"
