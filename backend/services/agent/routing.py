"""조건 분기 함수 — Graph 엣지에서 사용하는 라우팅 로직.

script_graph.py의 파일 크기를 줄이기 위해 분리.
"""

from __future__ import annotations

from config import LANGGRAPH_MAX_REVISIONS, logger
from services.agent.state import ScriptState


def route_after_start(state: ScriptState) -> str:
    """START 이후: mode에 따라 research(full) 또는 draft(quick) 분기."""
    mode = state.get("mode", "quick")
    if mode == "full":
        return "research"
    return "draft"


def route_after_review(state: ScriptState) -> str:
    """review 이후: passed → cinematographer(full)/finalize(quick), failed → revise.

    Quick → finalize 직행, Full → cinematographer (Production chain 시작).
    """
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


def route_after_copyright(state: ScriptState) -> str:
    """copyright_reviewer 이후: auto_approve → finalize, else → human_gate."""
    if state.get("auto_approve"):
        return "finalize"
    return "human_gate"


def route_after_human_gate(state: ScriptState) -> str:
    """Human Gate 이후: approve → finalize, revise → revise."""
    action = state.get("human_action", "approve")
    if action == "revise":
        return "revise"
    return "finalize"
