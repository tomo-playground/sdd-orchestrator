"""Phase 9-5B: Concept Gate 단위 테스트.

concept_gate 노드, writer 컨셉 주입, 그래프 구조, 스키마, SSE 읽기를 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.script_graph import build_script_graph

# -- Fixtures --


@pytest.fixture
def sample_critic_result():
    """critic_node가 반환하는 전형적인 결과."""
    return {
        "selected_concept": {
            "agent_role": "storyteller",
            "title": "잃어버린 기억",
            "concept": "주인공이 기억을 되찾아가는 여정",
            "strengths": ["감정선이 강함"],
            "weaknesses": ["전개가 느림"],
        },
        "candidates": [
            {
                "agent_role": "storyteller",
                "title": "잃어버린 기억",
                "concept": "주인공이 기억을 되찾아가는 여정",
            },
            {
                "agent_role": "comedian",
                "title": "웃음의 힘",
                "concept": "코미디로 세상을 바꾸는 이야기",
            },
            {
                "agent_role": "philosopher",
                "title": "존재의 이유",
                "concept": "삶의 의미를 탐구하는 철학적 여정",
            },
        ],
        "evaluation": {"best_agent_role": "storyteller", "best_score": 0.85},
    }


# -- concept_gate 노드 테스트 --


@pytest.mark.asyncio
async def test_concept_gate_auto_approve_passthrough(sample_critic_result):
    """Full Auto → {} 반환, interrupt 없음."""
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {"auto_approve": True, "critic_result": sample_critic_result}
    result = await concept_gate_node(state)
    assert result == {}


@pytest.mark.asyncio
@patch("services.agent.nodes.concept_gate.interrupt")
async def test_concept_gate_creator_interrupt(mock_interrupt, sample_critic_result):
    """Creator → interrupt 호출 확인."""
    mock_interrupt.return_value = {"concept_id": 1}
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {"auto_approve": False, "critic_result": sample_critic_result}
    result = await concept_gate_node(state)

    mock_interrupt.assert_called_once()
    call_args = mock_interrupt.call_args[0][0]
    assert call_args["type"] == "concept_selection"
    assert len(call_args["candidates"]) == 3
    # 사용자가 concept_id=1 선택 → comedian 컨셉
    assert result["critic_result"]["selected_concept"]["agent_role"] == "comedian"


@pytest.mark.asyncio
@patch("services.agent.nodes.concept_gate.interrupt")
async def test_concept_gate_updates_selected_concept(mock_interrupt, sample_critic_result):
    """사용자 선택 → critic_result.selected_concept 업데이트."""
    mock_interrupt.return_value = {"concept_id": 2}
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {"auto_approve": False, "critic_result": sample_critic_result}
    result = await concept_gate_node(state)

    assert result["critic_result"]["selected_concept"]["agent_role"] == "philosopher"
    assert result["critic_result"]["selected_concept"]["title"] == "존재의 이유"


@pytest.mark.asyncio
@patch("services.agent.nodes.concept_gate.interrupt")
async def test_concept_gate_invalid_id_fallback(mock_interrupt, sample_critic_result):
    """잘못된 concept_id → 첫 번째 컨셉 fallback."""
    mock_interrupt.return_value = {"concept_id": 99}
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {"auto_approve": False, "critic_result": sample_critic_result}
    result = await concept_gate_node(state)

    assert result["critic_result"]["selected_concept"]["agent_role"] == "storyteller"


# -- writer 컨셉 주입 테스트 --


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_writer_injects_selected_concept(mock_db_ctx, mock_gen_script, sample_critic_result):
    """writer가 선정 컨셉을 description에 주입."""
    mock_gen_script.return_value = {"scenes": [{"script": "test", "speaker": "A", "duration": 3}]}
    from services.agent.nodes.writer import writer_node

    state = {
        "topic": "테스트",
        "description": "원본 설명",
        "duration": 10,
        "critic_result": sample_critic_result,
    }
    await writer_node(state)

    call_args = mock_gen_script.call_args
    request = call_args[0][0]
    assert "[선정 컨셉]" in request.description
    assert "잃어버린 기억" in request.description


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_writer_no_concept_no_injection(mock_db_ctx, mock_gen_script):
    """critic_result 없으면 주입 스킵."""
    mock_gen_script.return_value = {"scenes": [{"script": "test", "speaker": "A", "duration": 3}]}
    from services.agent.nodes.writer import writer_node

    state = {"topic": "테스트", "description": "원본 설명", "duration": 10}
    await writer_node(state)

    call_args = mock_gen_script.call_args
    request = call_args[0][0]
    assert "[선정 컨셉]" not in request.description


# -- 그래프 구조 테스트 --


def test_graph_has_concept_gate_node():
    """15노드 그래프에 concept_gate 존재 확인."""
    graph = build_script_graph()
    compiled = graph.compile()
    node_names = set(compiled.get_graph().nodes.keys())
    assert "concept_gate" in node_names


def test_graph_edge_critic_concept_gate_writer():
    """critic → concept_gate → writer 엣지 검증."""
    graph = build_script_graph()
    compiled = graph.compile()
    graph_data = compiled.get_graph()

    # concept_gate의 이웃 찾기 — 엣지 탐색
    edges = [(e.source, e.target) for e in graph_data.edges]
    assert ("critic", "concept_gate") in edges
    assert ("concept_gate", "writer") in edges
    # critic → writer 직통 엣지가 없어야 함
    assert ("critic", "writer") not in edges


# -- 스키마 테스트 --


def test_resume_request_with_concept_id():
    """ScriptResumeRequest에 concept_id 필드 존재."""
    from schemas import ScriptResumeRequest

    req = ScriptResumeRequest(thread_id="test-123", action="select", concept_id=1)
    assert req.concept_id == 1
    assert req.action == "select"

    # concept_id 없이도 유효
    req2 = ScriptResumeRequest(thread_id="test-456", action="approve")
    assert req2.concept_id is None


# -- _read_interrupt_state 테스트 --


@pytest.mark.asyncio
async def test_read_interrupt_state_concept_gate(sample_critic_result):
    """_read_interrupt_state가 concept_gate 타입 반환."""
    from routers.scripts import _read_interrupt_state

    mock_graph = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.values = {"critic_result": sample_critic_result}
    mock_snapshot.next = ("concept_gate",)
    mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)

    interrupt_node, result = await _read_interrupt_state(mock_graph, {"configurable": {}})

    assert interrupt_node == "concept_gate"
    assert result["type"] == "concept_selection"
    assert len(result["candidates"]) == 3
    assert result["selected_concept"]["agent_role"] == "storyteller"
