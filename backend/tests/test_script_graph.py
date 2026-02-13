"""LangGraph Script Graph 단위 테스트.

generate_script를 mock하여 Graph 구조와 State 전파를 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.script_graph import build_script_graph
from services.agent.state import ScriptState


@pytest.fixture
def mock_scenes():
    return [
        {"scene_number": 1, "script": "테스트 씬 1", "tags": ["test"]},
        {"scene_number": 2, "script": "테스트 씬 2", "tags": ["test"]},
    ]


def test_graph_structure():
    """draft / finalize 노드가 Graph에 존재하는지 확인한다."""
    graph = build_script_graph()
    compiled = graph.compile()
    node_names = set(compiled.get_graph().nodes.keys())
    assert "draft" in node_names
    assert "finalize" in node_names


@pytest.mark.asyncio
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.SessionLocal")
async def test_graph_execution(mock_session_cls, mock_gen_script, mock_scenes):
    """mock Gemini → final_scenes 출력을 확인한다."""
    mock_db = mock_session_cls.return_value
    mock_gen_script.return_value = {"scenes": mock_scenes, "character_id": 42}

    graph = build_script_graph().compile()
    input_state: ScriptState = {"topic": "테스트 주제", "character_id": 42}
    result = await graph.ainvoke(input_state)

    assert result["final_scenes"] is not None
    assert len(result["final_scenes"]) == 2
    assert result["draft_character_id"] == 42
    mock_db.close.assert_called_once()


@pytest.mark.asyncio
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.SessionLocal")
async def test_graph_state_propagation(mock_session_cls, mock_gen_script, mock_scenes):
    """draft_scenes == final_scenes (패스스루)를 확인한다."""
    mock_gen_script.return_value = {"scenes": mock_scenes}

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "전파 테스트"})

    assert result["draft_scenes"] == result["final_scenes"]
    assert result["final_scenes"] == mock_scenes
