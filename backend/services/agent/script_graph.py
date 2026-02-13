"""Script Generation Graph — START → draft → finalize → END.

Phase 0: 2-노드 PoC (기존 generate_script 래핑).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from services.agent.nodes.draft import draft_node
from services.agent.nodes.finalize import finalize_node
from services.agent.state import ScriptState


def build_script_graph() -> StateGraph:
    """StateGraph를 구성한다. compile()은 호출자가 수행."""
    graph = StateGraph(ScriptState)
    graph.add_node("draft", draft_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "finalize")
    graph.add_edge("finalize", END)
    return graph


async def get_compiled_graph():
    """checkpointer를 주입하고 컴파일된 그래프를 반환한다."""
    from services.agent.checkpointer import get_checkpointer

    checkpointer = await get_checkpointer()
    return build_script_graph().compile(checkpointer=checkpointer)
