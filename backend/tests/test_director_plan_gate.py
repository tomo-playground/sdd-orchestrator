"""Phase 26: Director Plan Gate 단위 테스트.

director_plan_gate 노드, 라우팅, 그래프 구조, SSE interrupt 읽기를 검증한다.
"""

from __future__ import annotations

from unittest.mock import patch

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
async def test_director_plan_gate_fast_track_passthrough(sample_director_plan):
    """FastTrack 모드 → pass-through, interrupt 없음."""
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {"interaction_mode": "fast_track", "director_plan": sample_director_plan}
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
async def test_director_plan_gate_guided_interrupt_with_skip_stages(mock_interrupt, sample_director_plan):
    """Guided 모드 + skip_stages → interrupt 호출 확인."""
    mock_interrupt.return_value = {"action": "proceed"}
    from services.agent.nodes.director_plan_gate import director_plan_gate_node

    state = {
        "interaction_mode": "guided",
        "director_plan": sample_director_plan,
        "skip_stages": ["research"],
    }
    result = await director_plan_gate_node(state)

    mock_interrupt.assert_called_once()
    assert result == {"plan_action": "proceed"}


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan_gate.interrupt")
async def test_director_plan_gate_revise_plan(mock_interrupt, sample_director_plan):
    """사용자 revise_plan → revision_feedback 필드에 피드백 저장, description 누적 없음."""
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
    assert result["revision_feedback"] == "감정선을 더 강하게"
    # description에 피드백이 누적되지 않아야 함
    assert "description" not in result
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


# -- route_after_director 모드 분기 테스트 --


def test_route_director_approve_guided():
    """Director approve + guided → finalize."""
    state = {"director_decision": "approve", "interaction_mode": "guided"}
    assert route_after_director(state) == "finalize"


def test_route_director_approve_fast_track():
    """Director approve + fast_track → finalize."""
    state = {"director_decision": "approve", "interaction_mode": "fast_track"}
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
