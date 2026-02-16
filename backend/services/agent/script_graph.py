"""Script Generation Graph — 12노드 조건 분기 그래프.

Quick: START → draft → review → [passed→finalize / failed→revise] → learn → END
Full:  START → research → debate → draft → review →
       [passed→cinematographer / failed→revise] →
       tts_designer → sound_designer → copyright_reviewer →
       [auto→finalize / else→human_gate] → finalize → learn → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from services.agent.nodes.cinematographer import cinematographer_node
from services.agent.nodes.copyright_reviewer import copyright_reviewer_node
from services.agent.nodes.debate import debate_node
from services.agent.nodes.draft import draft_node
from services.agent.nodes.finalize import finalize_node
from services.agent.nodes.human_gate import human_gate_node
from services.agent.nodes.learn import learn_node
from services.agent.nodes.research import research_node
from services.agent.nodes.review import review_node
from services.agent.nodes.revise import revise_node
from services.agent.nodes.sound_designer import sound_designer_node
from services.agent.nodes.tts_designer import tts_designer_node
from services.agent.routing import (
    route_after_copyright,
    route_after_human_gate,
    route_after_review,
    route_after_start,
)
from services.agent.state import ScriptState


def build_script_graph() -> StateGraph:
    """12노드 StateGraph를 구성한다. compile()은 호출자가 수행."""
    graph = StateGraph(ScriptState)

    # 노드 등록
    graph.add_node("research", research_node)
    graph.add_node("debate", debate_node)
    graph.add_node("draft", draft_node)
    graph.add_node("review", review_node)
    graph.add_node("revise", revise_node)
    graph.add_node("cinematographer", cinematographer_node)
    graph.add_node("tts_designer", tts_designer_node)
    graph.add_node("sound_designer", sound_designer_node)
    graph.add_node("copyright_reviewer", copyright_reviewer_node)
    graph.add_node("human_gate", human_gate_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("learn", learn_node)

    # START → mode 분기 (quick→draft, full→research)
    graph.add_conditional_edges(START, route_after_start, ["research", "draft"])

    # research → debate → draft → review
    graph.add_edge("research", "debate")
    graph.add_edge("debate", "draft")
    graph.add_edge("draft", "review")

    # review → cinematographer(full) | finalize(quick) | revise
    graph.add_conditional_edges(
        "review",
        route_after_review,
        ["finalize", "cinematographer", "revise"],
    )

    # revise → review (루프)
    graph.add_edge("revise", "review")

    # Production chain: cinematographer → tts → sound → copyright
    graph.add_edge("cinematographer", "tts_designer")
    graph.add_edge("tts_designer", "sound_designer")
    graph.add_edge("sound_designer", "copyright_reviewer")

    # copyright → human_gate | finalize (auto_approve)
    graph.add_conditional_edges(
        "copyright_reviewer",
        route_after_copyright,
        ["finalize", "human_gate"],
    )

    # human_gate → finalize | revise
    graph.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        ["finalize", "revise"],
    )

    # finalize → learn → END
    graph.add_edge("finalize", "learn")
    graph.add_edge("learn", END)

    return graph


async def get_compiled_graph():
    """checkpointer + store를 주입하고 컴파일된 그래프를 반환한다."""
    from services.agent.checkpointer import get_checkpointer
    from services.agent.store import get_store

    checkpointer = await get_checkpointer()
    store = await get_store()
    return build_script_graph().compile(checkpointer=checkpointer, store=store)
