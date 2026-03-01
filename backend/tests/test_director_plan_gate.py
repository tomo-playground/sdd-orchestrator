"""Phase 26: Director Plan Gate 단위 테스트.

director_plan_gate 노드, 라우팅, 그래프 구조, SSE interrupt 읽기를 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.routing import route_after_director, route_after_director_plan_gate
from services.agent.script_graph import build_script_graph


# -- Fixtures --


@pytest.fixture
def sample_director_plan():
    """director_plan_node가 반환하는 전형적인 결과."""
    return {
        "creative_goal": "일상 속 작은 감동을 전달",
        "target_emotion": "공감과 위로",
        "execution_plan": {"skip_stages": []},
    }


# -- director_plan_gate 노드 테스트 --


@pytest.mark.asyncio
async def test_director_plan_gate_auto_passthrough(sample_director_plan):
    """Auto 모드 → pass-through, interrupt 없음."""
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {"interaction_mode": "auto", "director_plan": sample_director_plan}
    result = await director_plan_gate_node(state)
    assert result == {"plan_action": "proceed"}


@pytest.mark.asyncio
async def test_director_plan_gate_auto_approve_fallback(sample_director_plan):
    """auto_approve=True (레거시) → pass-through."""
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {"auto_approve": True, "director_plan": sample_director_plan}
    result = await director_plan_gate_node(state)
    assert result == {"plan_action": "proceed"}


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan_gate.interrupt")
async def test_director_plan_gate_guided_interrupt(mock_interrupt, sample_director_plan):
    """Guided 모드 → interrupt 호출 확인."""
    mock_interrupt.return_value = {"action": "proceed"}
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {
        "interaction_mode": "guided",
        "director_plan": sample_director_plan,
        "skip_stages": [],
    }
    result = await director_plan_gate_node(state)

    mock_interrupt.assert_called_once()
    call_args = mock_interrupt.call_args[0][0]
    assert call_args["type"] == "plan_review"
    assert call_args["director_plan"] == sample_director_plan
    assert result == {"plan_action": "proceed"}


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan_gate.interrupt")
async def test_director_plan_gate_hands_on_interrupt(mock_interrupt, sample_director_plan):
    """Hands-on 모드 → interrupt 호출 확인."""
    mock_interrupt.return_value = {"action": "proceed"}
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {
        "interaction_mode": "hands_on",
        "director_plan": sample_director_plan,
        "skip_stages": ["research"],
    }
    result = await director_plan_gate_node(state)

    mock_interrupt.assert_called_once()
    assert result == {"plan_action": "proceed"}


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan_gate.interrupt")
async def test_director_plan_gate_revise_plan(mock_interrupt, sample_director_plan):
    """사용자 revise_plan → description에 피드백 합류."""
    mock_interrupt.return_value = {"action": "revise_plan", "feedback": "감정선을 더 강하게"}
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {
        "interaction_mode": "guided",
        "director_plan": sample_director_plan,
        "description": "원본 설명",
        "plan_revision_count": 0,
        "skip_stages": [],
    }
    result = await director_plan_gate_node(state)

    assert result["plan_action"] == "revise"
    assert "[사용자 피드백] 감정선을 더 강하게" in result["description"]
    assert result["plan_revision_count"] == 1


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan_gate.interrupt")
async def test_director_plan_gate_revise_max_count(mock_interrupt, sample_director_plan):
    """plan_revision_count > 2 → 강제 proceed."""
    mock_interrupt.return_value = {"action": "revise_plan", "feedback": "다시 수정"}
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {
        "interaction_mode": "guided",
        "director_plan": sample_director_plan,
        "description": "원본 설명",
        "plan_revision_count": 2,
        "skip_stages": [],
    }
    result = await director_plan_gate_node(state)

    assert result["plan_action"] == "proceed"
    assert result["plan_revision_count"] == 3


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan_gate.interrupt")
async def test_director_plan_gate_second_revise_allowed(mock_interrupt, sample_director_plan):
    """plan_revision_count=1 → 두 번째 revise 허용."""
    mock_interrupt.return_value = {"action": "revise_plan", "feedback": "조금 더 수정"}
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {
        "interaction_mode": "guided",
        "director_plan": sample_director_plan,
        "description": "원본 설명",
        "plan_revision_count": 1,
        "skip_stages": [],
    }
    result = await director_plan_gate_node(state)

    assert result["plan_action"] == "revise"
    assert result["plan_revision_count"] == 2


# -- route_after_director_plan_gate 테스트 --


def test_route_plan_gate_proceed():
    """plan_action=proceed → inventory_resolve."""
    assert route_after_director_plan_gate({"plan_action": "proceed"}) == "inventory_resolve"


def test_route_plan_gate_revise():
    """plan_action=revise → director_plan (재수립)."""
    assert route_after_director_plan_gate({"plan_action": "revise"}) == "director_plan"


def test_route_plan_gate_default():
    """plan_action 없음 → inventory_resolve (기본값)."""
    assert route_after_director_plan_gate({}) == "inventory_resolve"


# -- route_after_director hands_on 분기 테스트 --


def test_route_director_approve_hands_on():
    """Director approve + hands_on → human_gate."""
    state = {"director_decision": "approve", "interaction_mode": "hands_on"}
    assert route_after_director(state) == "human_gate"


def test_route_director_approve_guided():
    """Director approve + guided → finalize (human_gate 스킵)."""
    state = {"director_decision": "approve", "interaction_mode": "guided"}
    assert route_after_director(state) == "finalize"


def test_route_director_approve_auto():
    """Director approve + auto → finalize."""
    state = {"director_decision": "approve", "interaction_mode": "auto"}
    assert route_after_director(state) == "finalize"


# -- 그래프 구조 테스트 --


def test_graph_has_director_plan_gate_node():
    """19노드 그래프에 director_plan_gate 존재 확인."""
    graph = build_script_graph()
    compiled = graph.compile()
    node_names = set(compiled.get_graph().nodes.keys())
    assert "director_plan_gate" in node_names


def test_graph_edge_director_plan_to_gate():
    """director_plan → director_plan_gate 엣지 검증."""
    graph = build_script_graph()
    compiled = graph.compile()
    graph_data = compiled.get_graph()
    edges = [(e.source, e.target) for e in graph_data.edges]
    assert ("director_plan", "director_plan_gate") in edges
    assert ("director_plan_gate", "inventory_resolve") in edges
    assert ("director_plan_gate", "director_plan") in edges


# -- _read_interrupt_state 테스트 --


@pytest.mark.asyncio
async def test_read_interrupt_state_director_plan_gate(sample_director_plan):
    """_read_interrupt_state가 director_plan_gate 타입 반환."""
    from routers.scripts import _read_interrupt_state

    mock_graph = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.values = {
        "director_plan": sample_director_plan,
        "skip_stages": ["research"],
    }
    mock_snapshot.next = ("director_plan_gate",)
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    interrupt_node, result = await _read_interrupt_state(mock_graph, {"configurable": {}})

    assert interrupt_node == "director_plan_gate"
    assert result["type"] == "plan_review"
    assert result["director_plan"] == sample_director_plan
    assert result["skip_stages"] == ["research"]
