"""Script Generation Graph — 15노드 조건 분기 그래프 (에러 short-circuit + 병렬 fan-out).

Quick: START → writer → review → [passed→finalize / failed→revise] → learn → END
Full:  START → research → critic → concept_gate → writer → review →
       [passed→cinematographer / failed→revise] →
       ┌→ tts_designer ────┐
       ├→ sound_designer ──┤→ director → [human_gate] → finalize → explain → learn → END
       └→ copyright_reviewer┘

에러 발생 시: 어떤 노드든 error 설정 → 다음 분기에서 finalize로 short-circuit.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from services.agent.nodes.cinematographer import cinematographer_node
from services.agent.nodes.concept_gate import concept_gate_node
from services.agent.nodes.copyright_reviewer import copyright_reviewer_node
from services.agent.nodes.critic import critic_node
from services.agent.nodes.director import director_node
from services.agent.nodes.explain import explain_node
from services.agent.nodes.finalize import finalize_node
from services.agent.nodes.human_gate import human_gate_node
from services.agent.nodes.learn import learn_node
from services.agent.nodes.research import research_node
from services.agent.nodes.review import review_node
from services.agent.nodes.revise import revise_node
from services.agent.nodes.sound_designer import sound_designer_node
from services.agent.nodes.tts_designer import tts_designer_node
from services.agent.nodes.writer import writer_node
from services.agent.routing import (
    route_after_cinematographer,
    route_after_director,
    route_after_finalize,
    route_after_human_gate,
    route_after_review,
    route_after_start,
    route_after_writer,
)
from services.agent.state import ScriptState


def build_script_graph() -> StateGraph:
    """15노드 StateGraph를 구성한다. compile()은 호출자가 수행."""
    graph = StateGraph(ScriptState)

    # 노드 등록
    graph.add_node("research", research_node)
    graph.add_node("critic", critic_node)
    graph.add_node("concept_gate", concept_gate_node)
    graph.add_node("writer", writer_node)
    graph.add_node("review", review_node)
    graph.add_node("revise", revise_node)
    graph.add_node("cinematographer", cinematographer_node)
    graph.add_node("tts_designer", tts_designer_node)
    graph.add_node("sound_designer", sound_designer_node)
    graph.add_node("copyright_reviewer", copyright_reviewer_node)
    graph.add_node("director", director_node)
    graph.add_node("human_gate", human_gate_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("explain", explain_node)
    graph.add_node("learn", learn_node)

    # START → mode 분기 (quick→writer, full→research)
    graph.add_conditional_edges(START, route_after_start, ["research", "writer"])

    # research → critic → concept_gate → writer
    graph.add_edge("research", "critic")
    graph.add_edge("critic", "concept_gate")
    graph.add_edge("concept_gate", "writer")

    # writer → review | finalize (에러 short-circuit)
    graph.add_conditional_edges("writer", route_after_writer, ["review", "finalize"])

    # review → cinematographer(full) | finalize(quick/error) | revise
    graph.add_conditional_edges(
        "review",
        route_after_review,
        ["finalize", "cinematographer", "revise"],
    )

    # revise → review (루프)
    graph.add_edge("revise", "review")

    # Production fan-out: cinematographer → [tts, sound, copyright] 병렬
    graph.add_conditional_edges(
        "cinematographer",
        route_after_cinematographer,
        ["tts_designer", "sound_designer", "copyright_reviewer", "finalize"],
    )

    # Fan-in: 3개 → director (LangGraph가 모두 완료될 때까지 자동 대기)
    graph.add_edge("tts_designer", "director")
    graph.add_edge("sound_designer", "director")
    graph.add_edge("copyright_reviewer", "director")

    # director → human_gate | finalize | production 노드 재실행 | revise
    graph.add_conditional_edges(
        "director",
        route_after_director,
        ["finalize", "human_gate", "cinematographer", "tts_designer", "sound_designer", "revise"],
    )

    # human_gate → finalize | revise
    graph.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        ["finalize", "revise"],
    )

    # finalize → [explain(full) | learn(quick)]
    graph.add_conditional_edges(
        "finalize",
        route_after_finalize,
        ["explain", "learn"],
    )

    # explain → learn → END
    graph.add_edge("explain", "learn")
    graph.add_edge("learn", END)

    return graph


async def get_compiled_graph():
    """checkpointer + store를 주입하고 컴파일된 그래프를 반환한다."""
    from services.agent.checkpointer import get_checkpointer
    from services.agent.store import get_store

    checkpointer = await get_checkpointer()
    store = await get_store()
    return build_script_graph().compile(checkpointer=checkpointer, store=store)
