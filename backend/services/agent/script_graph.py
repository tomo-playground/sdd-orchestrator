"""Script Generation Graph — 20노드 조건 분기 그래프 (에러 short-circuit + 병렬 fan-out).

Guided/FastTrack 공통 경로 (SP-057: 모든 노드 1회 실행):
  START → director_plan → director_plan_gate → inventory_resolve →
  [research → critic / critic(research skip)] →
  concept_gate → location_planner → writer → review →
  [passed→director_checkpoint / failed→revise] →
  [proceed→cinematographer / revise→writer (재생성)] →
  ┌→ tts_designer ────┐
  ├→ sound_designer ──┤→ director → finalize → explain → learn → END
  └→ copyright_reviewer┘

FastTrack: gate 자동 승인 + Critic/Director 반복 1회 제한.
Guided: gate에서 interrupt로 사용자 선택 대기.
에러 발생 시: 어떤 노드든 error 설정 → 다음 분기에서 finalize로 short-circuit.
"""

from __future__ import annotations

import functools
from contextlib import asynccontextmanager
from typing import Any

from langgraph.graph import END, START, StateGraph

from services.agent.nodes.cinematographer import cinematographer_node
from services.agent.nodes.concept_gate import concept_gate_node
from services.agent.nodes.copyright_reviewer import copyright_reviewer_node
from services.agent.nodes.critic import critic_node
from services.agent.nodes.director import director_node
from services.agent.nodes.director_checkpoint import director_checkpoint_node
from services.agent.nodes.director_plan import director_plan_node
from services.agent.nodes.director_plan_gate import director_plan_gate_node
from services.agent.nodes.explain import explain_node
from services.agent.nodes.finalize import finalize_node
from services.agent.nodes.human_gate import human_gate_node
from services.agent.nodes.learn import learn_node
from services.agent.nodes.location_planner import location_planner_node
from services.agent.nodes.research import research_node
from services.agent.nodes.review import review_node
from services.agent.nodes.revise import revise_node
from services.agent.nodes.sound_designer import sound_designer_node
from services.agent.nodes.tts_designer import tts_designer_node
from services.agent.nodes.writer import writer_node
from services.agent.observability import trace_agent, with_starting_event
from services.agent.routing import (
    route_after_cinematographer,
    route_after_concept_gate,
    route_after_director,
    route_after_director_checkpoint,
    route_after_director_plan_gate,
    route_after_finalize,
    route_after_human_gate,
    route_after_inventory_resolve,
    route_after_location_planner,
    route_after_research,
    route_after_review,
    route_after_revise,
    route_after_start,
    route_after_writer,
)
from services.agent.state import ScriptState

# AGENT observation에 기록할 state 요약 키
_STATE_SUMMARY_KEYS = ("skip_stages", "revision_count", "interaction_mode", "error")


def _wrap_node(name: str, fn: Any) -> Any:
    """노드 함수를 starting 이벤트 발행 + AGENT observation으로 래핑한다."""
    inner = with_starting_event(name)(fn)

    @functools.wraps(fn)
    async def wrapped(state, *args, **kwargs):  # noqa: ANN001
        input_summary = {k: state.get(k) for k in _STATE_SUMMARY_KEYS if state.get(k) is not None}
        async with trace_agent(name, input_data=input_summary or None) as agent_obs:
            result = await inner(state, *args, **kwargs)
            if agent_obs and isinstance(result, dict):
                agent_obs.update(output={"updated_keys": list(result.keys())})
        return result

    return wrapped


def build_script_graph() -> StateGraph:
    """20노드 StateGraph를 구성한다. compile()은 호출자가 수행."""
    from services.agent.nodes.inventory_resolve import inventory_resolve_node  # noqa: PLC0415

    graph = StateGraph(ScriptState)

    # 노드 등록 (20개) — AGENT observation 래핑
    graph.add_node("director_plan", _wrap_node("director_plan", director_plan_node))
    graph.add_node("director_plan_gate", _wrap_node("director_plan_gate", director_plan_gate_node))
    graph.add_node("inventory_resolve", _wrap_node("inventory_resolve", inventory_resolve_node))
    graph.add_node("research", _wrap_node("research", research_node))
    graph.add_node("critic", _wrap_node("critic", critic_node))
    graph.add_node("concept_gate", _wrap_node("concept_gate", concept_gate_node))
    graph.add_node("location_planner", _wrap_node("location_planner", location_planner_node))
    graph.add_node("writer", _wrap_node("writer", writer_node))
    graph.add_node("review", _wrap_node("review", review_node))
    graph.add_node("revise", _wrap_node("revise", revise_node))
    graph.add_node("director_checkpoint", _wrap_node("director_checkpoint", director_checkpoint_node))
    graph.add_node("cinematographer", _wrap_node("cinematographer", cinematographer_node))
    graph.add_node("tts_designer", _wrap_node("tts_designer", tts_designer_node))
    graph.add_node("sound_designer", _wrap_node("sound_designer", sound_designer_node))
    graph.add_node("copyright_reviewer", _wrap_node("copyright_reviewer", copyright_reviewer_node))
    graph.add_node("director", _wrap_node("director", director_node))
    graph.add_node("human_gate", _wrap_node("human_gate", human_gate_node))
    graph.add_node("finalize", _wrap_node("finalize", finalize_node))
    graph.add_node("explain", _wrap_node("explain", explain_node))
    graph.add_node("learn", _wrap_node("learn", learn_node))

    # START → 2분기 (skip_stages 직접 지정→writer, 기본→director_plan)
    graph.add_conditional_edges(START, route_after_start, ["director_plan", "writer"])

    # director_plan → director_plan_gate → inventory_resolve | director_plan (재수립)
    graph.add_edge("director_plan", "director_plan_gate")
    graph.add_conditional_edges(
        "director_plan_gate",
        route_after_director_plan_gate,
        ["inventory_resolve", "director_plan"],
    )

    # inventory_resolve → 조건부 (research skip→critic, full→research)
    graph.add_conditional_edges("inventory_resolve", route_after_inventory_resolve, ["research", "critic"])
    graph.add_conditional_edges("research", route_after_research, ["critic", "research", "finalize"])
    graph.add_edge("critic", "concept_gate")
    graph.add_conditional_edges("concept_gate", route_after_concept_gate, ["location_planner", "critic"])
    graph.add_conditional_edges("location_planner", route_after_location_planner, ["writer", "finalize"])

    # writer → review | finalize (에러 short-circuit)
    graph.add_conditional_edges("writer", route_after_writer, ["review", "finalize"])

    # review → director_checkpoint | finalize(error) | revise
    graph.add_conditional_edges(
        "review",
        route_after_review,
        ["finalize", "director_checkpoint", "revise"],
    )

    # revise → review | finalize (에러 short-circuit)
    graph.add_conditional_edges("revise", route_after_revise, ["review", "finalize"])

    # director_checkpoint → cinematographer | writer (재생성) | finalize
    graph.add_conditional_edges(
        "director_checkpoint",
        route_after_director_checkpoint,
        ["cinematographer", "writer", "finalize"],
    )

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

    # director → finalize | production 노드 재실행 | revise
    graph.add_conditional_edges(
        "director",
        route_after_director,
        ["finalize", "cinematographer", "tts_designer", "sound_designer", "revise"],
    )

    # human_gate → finalize | revise (안전 fallback — 도달 경로 없음)
    graph.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        ["finalize", "revise"],
    )

    # finalize → explain (에러 시 learn 직행)
    graph.add_conditional_edges(
        "finalize",
        route_after_finalize,
        ["explain", "learn"],
    )

    # explain → learn → END
    graph.add_edge("explain", "learn")
    graph.add_edge("learn", END)

    return graph


@asynccontextmanager
async def get_compiled_graph():
    """요청별 checkpointer를 주입하고 컴파일된 그래프를 yield한다."""
    from services.agent.checkpointer import get_checkpointer
    from services.agent.store import get_store

    async with get_checkpointer() as checkpointer:
        store = await get_store()
        yield build_script_graph().compile(checkpointer=checkpointer, store=store)
