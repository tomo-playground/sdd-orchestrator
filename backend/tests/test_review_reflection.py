"""Review Self-Reflection 테스트 (Phase 10-A).

Review 실패 시 근본 원인 분석 + 구체적 수정 전략이 생성되고,
Revise 노드에 전달되는지 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("config.gemini_client")
@patch("services.agent.nodes.review.template_env")
async def test_self_reflect_success(mock_tenv, mock_gemini):
    """Self-Reflection이 성공적으로 근본 원인 + 수정 전략을 생성한다."""
    from services.agent.nodes.review import _self_reflect

    mock_tenv.get_template.return_value.render.return_value = "prompt"

    # Gemini 응답 mock (JSON 형식)
    mock_response = MagicMock()
    mock_response.text = """{
        "root_cause": "씬 개수가 부족하고 Hook이 약합니다.",
        "impact": "영상이 짧고 청자의 관심을 끌지 못합니다.",
        "strategy": "씬 1의 스크립트를 질문형으로 변경하고, 씬 2-3을 추가하여 Rising Action을 강화하세요.",
        "expected_outcome": "Hook이 강화되고 전체 흐름이 자연스러워집니다."
    }"""
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    review_result = {
        "passed": False,
        "errors": ["씬 개수 부족: 2개 (최소 5개 필요)"],
        "warnings": [],
    }

    reflection = await _self_reflect(
        review_result=review_result,
        topic="AI의 미래",
        language="Korean",
        structure="Monologue",
    )

    assert reflection is not None
    assert "씬 개수가 부족하고 Hook이 약합니다" in reflection
    assert "근본 원인" in reflection
    assert "수정 전략" in reflection


@pytest.mark.asyncio
@patch("config.gemini_client")
async def test_self_reflect_gemini_error(mock_gemini):
    """Gemini 에러 시 None을 반환한다 (graceful degradation)."""
    from services.agent.nodes.review import _self_reflect

    mock_gemini.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("API error"))

    review_result = {
        "passed": False,
        "errors": ["씬 개수 부족"],
        "warnings": [],
    }

    reflection = await _self_reflect(
        review_result=review_result,
        topic="테스트",
        language="Korean",
        structure="Monologue",
    )

    assert reflection is None


@pytest.mark.asyncio
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
@patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock)
@patch("services.agent.nodes.review._gemini_evaluate", new_callable=AsyncMock)
async def test_review_node_calls_reflection_on_failure(mock_gemini_eval, mock_narrative, mock_reflect):
    """Review 실패 시 Self-Reflection을 호출한다."""
    from services.agent.nodes.review import review_node

    # Mock: 규칙 검증 실패 + Full 모드
    mock_gemini_eval.return_value = "씬 개수가 부족합니다."
    mock_reflect.return_value = "[근본 원인] 씬 개수 부족\n[수정 전략] 씬 추가"

    state = {
        "draft_scenes": [
            {"scene_id": 1, "script": "테스트", "speaker": "A", "duration": 3, "image_prompt": "smile"}
        ],
        "duration": 15,  # 최소 8개 씬 필요 → 실패
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트 주제",
        "mode": "full",
    }

    result = await review_node(state)

    # Self-Reflection 호출 확인
    assert mock_reflect.called
    assert result["review_reflection"] is not None
    assert "근본 원인" in result["review_reflection"]


@pytest.mark.asyncio
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
@patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock)
async def test_review_node_skips_reflection_on_success(mock_narrative, mock_reflect):
    """Review 통과 시 Self-Reflection을 호출하지 않는다."""
    from services.agent.nodes.review import review_node

    # Mock: 서사 품질도 통과 (임계값 0.6 이상)
    mock_narrative.return_value = {
        "hook": 0.8,
        "emotional_arc": 0.7,
        "twist_payoff": 0.6,
        "speaker_tone": 0.7,
        "script_image_sync": 0.8,
        "overall": 0.72,
        "feedback": "훌륭합니다.",
    }

    state = {
        "draft_scenes": [
            {"scene_id": i, "script": f"테스트 씬 {i}", "speaker": "A", "duration": 2, "image_prompt": "smile"}
            for i in range(1, 6)
        ],
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "mode": "full",
    }

    result = await review_node(state)

    # 규칙 통과 + 서사 품질 통과 → Self-Reflection 호출 안 함
    assert not mock_reflect.called
    assert result.get("review_reflection") is None


@pytest.mark.asyncio
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
async def test_review_node_skips_reflection_in_quick_mode(mock_reflect):
    """Quick 모드에서는 Self-Reflection을 호출하지 않는다."""
    from services.agent.nodes.review import review_node

    state = {
        "draft_scenes": [{"scene_id": 1, "script": "테스트", "speaker": "A", "duration": 3, "image_prompt": ""}],
        "duration": 15,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "mode": "quick",  # Quick 모드
    }

    result = await review_node(state)

    # Quick 모드 → Self-Reflection 호출 안 함
    assert not mock_reflect.called
    assert result.get("review_reflection") is None


@pytest.mark.asyncio
async def test_revise_includes_reflection_in_feedback():
    """Revise 노드가 reflection을 피드백에 포함한다."""
    from services.agent.nodes.revise import _build_feedback

    state = {
        "review_reflection": "[근본 원인]\n씬 개수 부족\n\n[수정 전략]\n씬 2-3개 추가",
        "review_result": {"errors": ["씬 개수 부족"]},
    }

    feedback = _build_feedback(state)

    assert "Review Self-Reflection" in feedback
    assert "근본 원인" in feedback
    assert "수정 전략" in feedback
    assert "검증 오류" in feedback


@pytest.mark.asyncio
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
@patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock)
async def test_review_narrative_failure_triggers_reflection(mock_narrative, mock_reflect):
    """서사 품질 미달 시에도 Self-Reflection을 호출한다."""
    from services.agent.nodes.review import review_node

    # Mock: 규칙 통과 + 서사 품질 미달
    mock_narrative.return_value = {
        "hook": 0.3,
        "emotional_arc": 0.4,
        "twist_payoff": 0.2,
        "speaker_tone": 0.5,
        "script_image_sync": 0.6,
        "overall": 0.4,  # 임계값(0.6) 미달
        "feedback": "Hook이 약합니다.",
    }
    mock_reflect.return_value = "[근본 원인] Hook 부족\n[수정 전략] 질문형으로 변경"

    state = {
        "draft_scenes": [
            {"scene_id": i, "script": f"씬 {i}", "speaker": "A", "duration": 2, "image_prompt": "smile"}
            for i in range(1, 6)
        ],
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "mode": "full",
    }

    result = await review_node(state)

    # 서사 품질 미달 → Self-Reflection 호출
    assert mock_reflect.called
    assert result["review_reflection"] is not None
    assert "Hook 부족" in result["review_reflection"]
