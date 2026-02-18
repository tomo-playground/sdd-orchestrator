"""Writer Planning Step 테스트 (Phase 10-A).

Writer가 Full 모드에서 계획 수립 후 생성하는지 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.state import ScriptState


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.gemini_client")
@patch("services.agent.nodes.writer.template_env")
async def test_create_plan_success(mock_tenv, mock_gemini):
    """Planning Step이 성공적으로 Hook 전략 + 감정 곡선 + 씬 배분을 생성한다."""
    from services.agent.nodes.writer import _create_plan

    mock_tenv.get_template.return_value.render.return_value = "prompt"

    # Gemini 응답 mock (JSON 형식)
    mock_response = MagicMock()
    mock_response.text = """{
        "hook_strategy": "Emotional Confession — '처음 고백했을 때, 심장이 터질 것 같았어'",
        "emotional_arc": ["두근거림", "긴장", "떨림", "안도", "여운"],
        "scene_distribution": {"intro": 1, "rising": 2, "climax": 1, "resolution": 1}
    }"""
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    state: ScriptState = {
        "topic": "첫 고백",
        "description": "첫 고백의 순간",
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
    }

    plan = await _create_plan(state)

    assert plan is not None
    assert "처음 고백했을 때" in plan["hook_strategy"]
    assert len(plan["emotional_arc"]) == 5
    assert plan["scene_distribution"]["intro"] == 1
    assert plan["scene_distribution"]["rising"] == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.gemini_client")
async def test_create_plan_gemini_error(mock_gemini):
    """Gemini 에러 시 None을 반환한다 (graceful degradation)."""
    from services.agent.nodes.writer import _create_plan

    mock_gemini.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("API error"))

    state: ScriptState = {
        "topic": "테스트",
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
    }

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
        "scenes": [
            {"scene_id": 1, "script": "테스트", "speaker": "A", "duration": 3, "image_prompt": "smile"}
        ],
    }

    state: ScriptState = {
        "topic": "테스트 주제",
        "mode": "full",
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
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
        "scenes": [
            {"scene_id": 1, "script": "테스트", "speaker": "A", "duration": 3, "image_prompt": "smile"}
        ],
    }

    state: ScriptState = {
        "topic": "테스트 주제",
        "mode": "quick",  # Quick 모드
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
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
            "mode": "full",
            "duration": 10,
            "language": "Korean",
            "structure": "Monologue",
            "actor_a_gender": "female",
        }

        result = await writer_node(state)

        # Planning 호출 안 함
        assert not mock_plan.called
        assert result.get("writer_plan") is None
