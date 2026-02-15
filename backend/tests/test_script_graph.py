"""LangGraph Script Graph 단위 테스트.

generate_script를 mock하여 Graph 구조와 State 전파를 검증한다.
8노드 그래프: research → debate → draft → review → revise/human_gate → finalize → learn
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.script_graph import build_script_graph
from services.agent.state import ScriptState


@pytest.fixture
def mock_scenes():
    """review 검증을 통과할 수 있는 유효한 씬 데이터."""
    return [
        {
            "scene_id": 1,
            "script": "테스트 씬 1입니다 안녕하세요",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "smile, looking_at_viewer, standing, indoors",
        },
        {
            "scene_id": 2,
            "script": "테스트 씬 2입니다 반갑습니다",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "happy, looking_at_viewer, sitting, outdoors",
        },
        {
            "scene_id": 3,
            "script": "테스트 씬 3입니다 감사합니다",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "smile, cowboy_shot, classroom, indoors",
        },
        {
            "scene_id": 4,
            "script": "테스트 씬 4입니다 좋은 하루요",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "waving, full_body, park, outdoors",
        },
        {
            "scene_id": 5,
            "script": "테스트 씬 5입니다 마지막이에요",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "smile, upper_body, sky, sunset",
        },
    ]


def test_graph_structure():
    """8노드가 모두 Graph에 존재하는지 확인한다."""
    graph = build_script_graph()
    compiled = graph.compile()
    node_names = set(compiled.get_graph().nodes.keys())
    for node in ("research", "debate", "draft", "review", "revise", "human_gate", "finalize", "learn"):
        assert node in node_names, f"'{node}' 노드가 그래프에 없음"


@pytest.mark.asyncio
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.get_db_session")
async def test_graph_quick_mode(mock_db_ctx, mock_gen_script, mock_scenes):
    """Quick 모드: draft → review(pass) → finalize → learn → END."""
    mock_gen_script.return_value = {"scenes": mock_scenes, "character_id": 42}

    graph = build_script_graph().compile()
    input_state: ScriptState = {
        "topic": "테스트 주제",
        "character_id": 42,
        "mode": "quick",
        "duration": 10,
    }
    result = await graph.ainvoke(input_state)

    assert result["final_scenes"] is not None
    assert len(result["final_scenes"]) == 5
    assert result["draft_character_id"] == 42


@pytest.mark.asyncio
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.get_db_session")
async def test_graph_state_propagation(mock_db_ctx, mock_gen_script, mock_scenes):
    """draft_scenes == final_scenes (review 통과 시 패스스루)를 확인한다."""
    mock_gen_script.return_value = {"scenes": mock_scenes}

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "전파 테스트", "mode": "quick", "duration": 10})

    assert result["draft_scenes"] == result["final_scenes"]
    assert result["final_scenes"] == mock_scenes


@pytest.mark.asyncio
@patch("services.agent.nodes.revise.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.revise.get_db_session")
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.get_db_session")
async def test_graph_revise_loop(
    mock_draft_db_ctx,
    mock_draft_gen,
    mock_revise_db_ctx,
    mock_revise_gen,
    mock_scenes,
):
    """Review 실패 → Revise → Review 통과 루프를 검증한다."""
    # draft: 불완전한 씬 반환 → review 실패
    bad_scenes = [{"script": "짧", "speaker": "A", "duration": 0, "image_prompt": ""}]
    mock_draft_gen.return_value = {"scenes": bad_scenes}

    # revise: 유효한 씬 반환 → review 통과
    mock_revise_gen.return_value = {"scenes": mock_scenes}

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "리비전 테스트", "mode": "quick", "duration": 10})

    assert result["final_scenes"] is not None
    assert result["revision_count"] >= 1
