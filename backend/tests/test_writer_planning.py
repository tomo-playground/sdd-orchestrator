"""Writer Planning Step 테스트 (Phase 10-A).

Writer가 Full 모드에서 계획 수립 후 생성하는지 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.state import ScriptState


@pytest.mark.asyncio
async def test_create_plan_success():
    """Planning Step이 성공적으로 Hook 전략 + 감정 곡선 + 씬 배분을 생성한다."""
    from services.agent.nodes.writer import _create_plan

    plan_json = """{
        "hook_strategy": "Emotional Confession — '처음 고백했을 때, 심장이 터질 것 같았어'",
        "emotional_arc": ["두근거림", "긴장", "떨림", "안도", "여운"],
        "scene_distribution": {"intro": 1, "rising": 2, "climax": 1, "resolution": 1}
    }"""
    mock_llm_resp = MagicMock()
    mock_llm_resp.text = plan_json

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

    state: ScriptState = {
        "topic": "첫 고백",
        "description": "첫 고백의 순간",
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
    }

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None

    with (
        patch("services.agent.nodes.writer.compile_prompt", return_value=mock_compiled),
        patch("services.agent.nodes.writer.get_llm_provider", return_value=mock_provider),
    ):
        plan = await _create_plan(state)

    assert plan is not None
    assert "처음 고백했을 때" in plan["hook_strategy"]
    assert len(plan["emotional_arc"]) == 5
    assert plan["scene_distribution"]["intro"] == 1
    assert plan["scene_distribution"]["rising"] == 2


@pytest.mark.asyncio
async def test_create_plan_gemini_error():
    """LLM 에러 시 None을 반환한다 (graceful degradation)."""
    from services.agent.nodes.writer import _create_plan

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=RuntimeError("API error"))

    state: ScriptState = {
        "topic": "테스트",
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
    }

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None

    with (
        patch("services.agent.nodes.writer.compile_prompt", return_value=mock_compiled),
        patch("services.agent.nodes.writer.get_llm_provider", return_value=mock_provider),
    ):
        plan = await _create_plan(state)

    assert plan is None


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
async def test_writer_node_calls_planning_in_full_mode(mock_gen, mock_plan):
    """Full 모드에서 Planning을 호출한다."""
    from services.agent.nodes.writer import writer_node

    # Mock Planning 결과
    mock_plan.return_value = {
        "hook_strategy": "질문형 Hook",
        "emotional_arc": ["호기심", "긴장", "반전", "여운"],
        "scene_distribution": {"intro": 1, "rising": 2, "resolution": 1},
    }

    # Mock 대본 생성 결과
    mock_gen.return_value = {
        "scenes": [{"scene_id": 1, "script": "테스트", "speaker": "speaker_1", "duration": 3, "image_prompt": "smile"}],
    }

    state: ScriptState = {
        "topic": "테스트 주제",
        "skip_stages": [],
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "actor_a_gender": "female",
    }

    result = await writer_node(state)

    # Planning 호출 확인
    assert mock_plan.called
    assert result["writer_plan"] is not None
    assert "질문형" in result["writer_plan"]["hook_strategy"]


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
async def test_writer_node_skips_planning_in_quick_mode(mock_gen, mock_plan):
    """Quick 모드에서는 Planning을 호출하지 않는다."""
    from services.agent.nodes.writer import writer_node

    mock_gen.return_value = {
        "scenes": [{"scene_id": 1, "script": "테스트", "speaker": "speaker_1", "duration": 3, "image_prompt": "smile"}],
    }

    state: ScriptState = {
        "topic": "테스트 주제",
        "skip_stages": ["research", "concept", "production", "explain"],  # Express 모드
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "actor_a_gender": "female",
    }

    result = await writer_node(state)

    # Planning 호출 안 함
    assert not mock_plan.called
    assert result.get("writer_plan") is None


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
async def test_writer_node_planning_disabled(mock_gen, mock_plan):
    """LANGGRAPH_PLANNING_ENABLED=False 시 Planning을 호출하지 않는다."""
    from services.agent.nodes.writer import writer_node

    # config를 임시로 수정
    with patch("services.agent.nodes.writer.LANGGRAPH_PLANNING_ENABLED", False):
        mock_gen.return_value = {"scenes": []}

        state: ScriptState = {
            "topic": "테스트",
            "skip_stages": [],
            "duration": 10,
            "language": "korean",
            "structure": "monologue",
            "actor_a_gender": "female",
        }

        result = await writer_node(state)

        # Planning 호출 안 함
        assert not mock_plan.called
        assert result.get("writer_plan") is None


# -- Location Map 테스트 (Phase 16+) --


@pytest.mark.asyncio
async def test_create_plan_with_locations():
    """LLM이 locations 포함 응답 시 파싱 성공."""
    from services.agent.nodes.writer import _create_plan

    plan_json = """{
        "hook_strategy": "Emotional Confession",
        "emotional_arc": ["긴장", "공감", "여운"],
        "scene_distribution": {"intro": 1, "rising": 1, "resolution": 1},
        "locations": [
            {"name": "piano_room", "scenes": [0, 1], "tags": ["piano", "stage", "indoors"]},
            {"name": "rooftop", "scenes": [2], "tags": ["rooftop", "outdoors", "sunset"]}
        ]
    }"""
    mock_llm_resp = MagicMock()
    mock_llm_resp.text = plan_json

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

    state: ScriptState = {
        "topic": "오래된 친구와의 재회",
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
    }

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None

    with (
        patch("services.agent.nodes.writer.compile_prompt", return_value=mock_compiled),
        patch("services.agent.nodes.writer.get_llm_provider", return_value=mock_provider),
    ):
        plan = await _create_plan(state)

    assert plan is not None
    assert "locations" in plan
    assert len(plan["locations"]) == 2
    assert plan["locations"][0]["name"] == "piano_room"
    assert 0 in plan["locations"][0]["scenes"]
    assert "stage" in plan["locations"][0]["tags"]
    assert plan["locations"][1]["name"] == "rooftop"


@pytest.mark.asyncio
async def test_create_plan_without_locations_backward_compat():
    """locations 없어도 기존 동작 유지 (후방 호환)."""
    from services.agent.nodes.writer import _create_plan

    plan_json = """{
        "hook_strategy": "질문형 Hook",
        "emotional_arc": ["호기심", "긴장", "여운"],
        "scene_distribution": {"intro": 1, "rising": 1, "resolution": 1}
    }"""
    mock_llm_resp = MagicMock()
    mock_llm_resp.text = plan_json

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

    state: ScriptState = {
        "topic": "테스트",
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
    }

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None

    with (
        patch("services.agent.nodes.writer.compile_prompt", return_value=mock_compiled),
        patch("services.agent.nodes.writer.get_llm_provider", return_value=mock_provider),
    ):
        plan = await _create_plan(state)

    assert plan is not None
    assert "hook_strategy" in plan
    assert "locations" not in plan


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
async def test_plan_text_includes_location_map(mock_gen, mock_plan):
    """plan_text에 Location Map 포함 확인."""
    from services.agent.nodes.writer import writer_node

    mock_plan.return_value = {
        "hook_strategy": "질문형 Hook",
        "emotional_arc": ["호기심", "긴장", "여운"],
        "scene_distribution": {"intro": 1, "rising": 1, "resolution": 1},
        "locations": [
            {"name": "piano_room", "scenes": [0, 1], "tags": ["piano", "stage", "indoors"]},
            {"name": "rooftop", "scenes": [2], "tags": ["rooftop", "outdoors"]},
        ],
    }
    mock_gen.return_value = {
        "scenes": [{"script": "테스트", "speaker": "speaker_1", "duration": 3, "image_prompt": "smile"}],
    }

    state: ScriptState = {
        "topic": "테스트",
        "skip_stages": [],
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "actor_a_gender": "female",
    }

    await writer_node(state)

    # generate_script에 전달된 pipeline_context 확인
    call_kwargs = mock_gen.call_args
    pipeline_ctx = call_kwargs.kwargs.get("pipeline_context") or call_kwargs[1].get("pipeline_context")
    writer_plan_text = pipeline_ctx["writer_plan"]

    assert "Location Map" in writer_plan_text
    assert "piano_room" in writer_plan_text
    assert "piano, stage, indoors" in writer_plan_text
    assert "rooftop" in writer_plan_text


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
async def test_plan_text_without_locations(mock_gen, mock_plan):
    """locations 없으면 Location Map 미포함."""
    from services.agent.nodes.writer import writer_node

    mock_plan.return_value = {
        "hook_strategy": "질문형 Hook",
        "emotional_arc": ["호기심", "긴장", "여운"],
        "scene_distribution": {"intro": 1, "rising": 1, "resolution": 1},
    }
    mock_gen.return_value = {
        "scenes": [{"script": "테스트", "speaker": "speaker_1", "duration": 3, "image_prompt": "smile"}],
    }

    state: ScriptState = {
        "topic": "테스트",
        "skip_stages": [],
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "actor_a_gender": "female",
    }

    await writer_node(state)

    call_kwargs = mock_gen.call_args
    pipeline_ctx = call_kwargs.kwargs.get("pipeline_context") or call_kwargs[1].get("pipeline_context")
    writer_plan_text = pipeline_ctx["writer_plan"]

    assert "Location Map" not in writer_plan_text
