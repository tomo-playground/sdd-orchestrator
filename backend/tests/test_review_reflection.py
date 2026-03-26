"""Review Self-Reflection 테스트 (Phase 10-A + Phase 13-A 통합).

Review 실패 시 근본 원인 분석 + 구체적 수정 전략이 생성되고,
Revise 노드에 전달되는지 검증한다.
Phase 13-A: 통합 Gemini 호출 + 레거시 폴백 검증.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── 레거시 개별 함수 테스트 ──


@pytest.mark.asyncio
@patch("services.agent.nodes.review.get_llm_provider")
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_self_reflect_success(mock_compile, mock_llm_provider):
    """Self-Reflection이 성공적으로 근본 원인 + 수정 전략을 생성한다."""
    from services.agent.nodes.review import _self_reflect

    mock_compiled = MagicMock()
    mock_compiled.system = "You are a self-reflection agent"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None
    mock_compile.return_value = mock_compiled

    # LLM 응답 mock (JSON 형식)
    mock_llm_resp = MagicMock()
    mock_llm_resp.text = """{
        "root_cause": "씬 개수가 부족하고 Hook이 약합니다.",
        "impact": "영상이 짧고 청자의 관심을 끌지 못합니다.",
        "strategy": "씬 1의 스크립트를 질문형으로 변경하고, 씬 2-3을 추가하여 Rising Action을 강화하세요.",
        "expected_outcome": "Hook이 강화되고 전체 흐름이 자연스러워집니다."
    }"""
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)
    mock_llm_provider.return_value = mock_provider

    review_result = {
        "passed": False,
        "errors": ["씬 개수 부족: 2개 (최소 5개 필요)"],
        "warnings": [],
    }

    reflection = await _self_reflect(
        review_result=review_result,
        topic="AI의 미래",
        language="korean",
        structure="monologue",
    )

    assert reflection is not None
    assert "씬 개수가 부족하고 Hook이 약합니다" in reflection
    assert "근본 원인" in reflection
    assert "수정 전략" in reflection


@pytest.mark.asyncio
@patch("services.agent.nodes.review.get_llm_provider")
async def test_self_reflect_gemini_error(mock_llm_provider):
    """LLM 에러 시 None을 반환한다 (graceful degradation)."""
    from services.agent.nodes.review import _self_reflect

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=RuntimeError("API error"))
    mock_llm_provider.return_value = mock_provider

    review_result = {
        "passed": False,
        "errors": ["씬 개수 부족"],
        "warnings": [],
    }

    reflection = await _self_reflect(
        review_result=review_result,
        topic="테스트",
        language="korean",
        structure="monologue",
    )

    assert reflection is None


# ── 레거시 폴백 경로 테스트 (_unified_evaluate=None → 개별 호출) ──


@pytest.mark.asyncio
@patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=(None, None))
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
@patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock)
@patch("services.agent.nodes.review._gemini_evaluate", new_callable=AsyncMock)
async def test_review_node_legacy_fallback_on_failure(mock_gemini_eval, mock_narrative, mock_reflect, mock_unified):
    """통합 호출 실패 → 레거시 폴백: 규칙 실패 시 Self-Reflection 호출."""
    from services.agent.nodes.review import review_node

    mock_gemini_eval.return_value = "씬 개수가 부족합니다."
    mock_reflect.return_value = "[근본 원인] 씬 개수 부족\n[수정 전략] 씬 추가"

    state = {
        "draft_scenes": [
            {"scene_id": 1, "script": "테스트", "speaker": "speaker_1", "duration": 3, "image_prompt": "smile"}
        ],
        "duration": 15,
        "language": "korean",
        "structure": "monologue",
        "topic": "테스트 주제",
        "skip_stages": [],
    }

    result = await review_node(state)

    assert mock_unified.called
    assert mock_reflect.called
    assert result["review_reflection"] is not None
    assert "근본 원인" in result["review_reflection"]


@pytest.mark.asyncio
@patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=(None, None))
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
@patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock)
async def test_review_node_legacy_skips_reflection_on_success(mock_narrative, mock_reflect, mock_unified):
    """통합 호출 실패 → 레거시 폴백: 통과 시 reflection 없음."""
    from services.agent.nodes.review import review_node

    mock_narrative.return_value = {
        "hook": 0.8,
        "emotional_arc": 0.7,
        "twist_payoff": 0.6,
        "speaker_tone": 0.7,
        "script_image_sync": 0.8,
        "spoken_naturalness": 0.7,
        "retention_flow": 0.7,
        "pacing_rhythm": 0.7,
        "overall": 0.72,
        "feedback": "훌륭합니다.",
    }

    state = {
        "draft_scenes": [
            {"scene_id": i, "script": f"테스트 씬 {i}", "speaker": "speaker_1", "duration": 2, "image_prompt": "smile"}
            for i in range(1, 6)
        ],
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "topic": "테스트",
        "skip_stages": [],
    }

    result = await review_node(state)

    assert not mock_reflect.called
    assert result.get("review_reflection") is None


@pytest.mark.asyncio
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
async def test_review_node_skips_reflection_in_quick_mode(mock_reflect):
    """Quick 모드에서는 통합/레거시 모두 호출하지 않는다."""
    from services.agent.nodes.review import review_node

    state = {
        "draft_scenes": [
            {"scene_id": 1, "script": "테스트", "speaker": "speaker_1", "duration": 3, "image_prompt": ""}
        ],
        "duration": 15,
        "language": "korean",
        "structure": "monologue",
        "topic": "테스트",
        "skip_stages": ["research", "concept", "production", "explain"],
    }

    result = await review_node(state)

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
@patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=(None, None))
@patch("services.agent.nodes.review._self_reflect", new_callable=AsyncMock)
@patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock)
async def test_review_narrative_failure_triggers_reflection_legacy(mock_narrative, mock_reflect, mock_unified):
    """레거시 폴백: 서사 품질 미달 시에도 Self-Reflection을 호출한다."""
    from services.agent.nodes.review import review_node

    mock_narrative.return_value = {
        "hook": 0.3,
        "emotional_arc": 0.4,
        "twist_payoff": 0.2,
        "speaker_tone": 0.5,
        "script_image_sync": 0.6,
        "spoken_naturalness": 0.4,
        "retention_flow": 0.3,
        "pacing_rhythm": 0.3,
        "overall": 0.4,
        "feedback": "Hook이 약합니다.",
    }
    mock_reflect.return_value = "[근본 원인] Hook 부족\n[수정 전략] 질문형으로 변경"

    state = {
        "draft_scenes": [
            {"scene_id": i, "script": f"씬 {i}", "speaker": "speaker_1", "duration": 2, "image_prompt": "smile"}
            for i in range(1, 6)
        ],
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "topic": "테스트",
        "skip_stages": [],
    }

    result = await review_node(state)

    assert mock_reflect.called
    assert result["review_reflection"] is not None
    assert "Hook 부족" in result["review_reflection"]


# ── Phase 13-A: 헬퍼 함수 단위 테스트 ──


def test_build_narrative_score_calculates_overall():
    """_build_narrative_score가 가중치 overall을 올바르게 계산한다."""
    from services.agent.llm_models import NarrativeScoreOutput
    from services.agent.nodes.review import _build_narrative_score

    parsed = NarrativeScoreOutput(
        hook=1.0,
        emotional_arc=1.0,
        twist_payoff=1.0,
        speaker_tone=1.0,
        script_image_sync=1.0,
        spoken_naturalness=1.0,
        retention_flow=1.0,
        pacing_rhythm=1.0,
        feedback="만점",
    )
    score = _build_narrative_score(parsed)
    assert score["overall"] == 1.0
    assert score["feedback"] == "만점"


def test_build_narrative_score_empty_feedback():
    """_build_narrative_score가 빈 feedback도 처리한다."""
    from services.agent.llm_models import NarrativeScoreOutput
    from services.agent.nodes.review import _build_narrative_score

    parsed = NarrativeScoreOutput(
        hook=0.5,
        emotional_arc=0.5,
        twist_payoff=0.5,
        speaker_tone=0.5,
        script_image_sync=0.5,
        spoken_naturalness=0.5,
        retention_flow=0.5,
        pacing_rhythm=0.5,
    )
    score = _build_narrative_score(parsed)
    assert score["overall"] == 0.5
    assert "feedback" not in score


def test_format_reflection_output():
    """_format_reflection이 구조화된 텍스트를 반환한다."""
    from services.agent.llm_models import ReflectionOutput
    from services.agent.nodes.review import _format_reflection

    ref = ReflectionOutput(
        root_cause="Hook 약함",
        impact="시청자 이탈",
        strategy="질문형 변경",
        expected_outcome="개선 기대",
    )
    text = _format_reflection(ref)
    assert "[근본 원인]" in text
    assert "Hook 약함" in text
    assert "[수정 전략]" in text
    assert "질문형 변경" in text


# ── Phase 13-A: 통합 호출 경로 테스트 ──


def _make_unified_json(*, tech_passed=True, tech_feedback="", narrative_scores=None, reflection=None):
    """통합 응답 JSON 생성 헬퍼."""
    narr = narrative_scores or {
        "hook": 0.8,
        "emotional_arc": 0.7,
        "twist_payoff": 0.6,
        "speaker_tone": 0.7,
        "script_image_sync": 0.8,
        "spoken_naturalness": 0.7,
        "retention_flow": 0.7,
        "pacing_rhythm": 0.7,
        "feedback": "좋은 스크립트입니다.",
    }
    return json.dumps(
        {
            "technical": {
                "overall_score": 0.85 if tech_passed else 0.3,
                "passed": tech_passed,
                "feedback": tech_feedback,
                "scene_issues": [],
            },
            "narrative": narr,
            "reflection": reflection,
        }
    )


def _full_state(scene_count=5, duration=10):
    """테스트용 Full 모드 state."""
    return {
        "draft_scenes": [
            {"scene_id": i, "script": f"테스트 씬 {i}", "speaker": "speaker_1", "duration": 2, "image_prompt": "smile"}
            for i in range(1, scene_count + 1)
        ],
        "duration": duration,
        "language": "korean",
        "structure": "monologue",
        "topic": "테스트 주제",
        "skip_stages": [],
    }


@pytest.mark.asyncio
@patch("services.agent.nodes.review.get_llm_provider")
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_unified_all_pass_no_reflection(mock_compile, mock_llm_provider):
    """통합 호출: technical pass + narrative pass → reflection null."""
    from services.agent.nodes.review import review_node

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None
    mock_compile.return_value = mock_compiled

    mock_llm_resp = MagicMock()
    mock_llm_resp.text = _make_unified_json(tech_passed=True, reflection=None)
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)
    mock_llm_provider.return_value = mock_provider

    result = await review_node(_full_state())

    assert result["review_result"]["passed"] is True
    assert result.get("review_reflection") is None
    assert result["review_result"].get("narrative_score") is not None
    assert result["review_result"]["narrative_score"]["overall"] > 0


@pytest.mark.asyncio
@patch("services.agent.nodes.review.get_llm_provider")
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_unified_narrative_fail_with_reflection(mock_compile, mock_llm_provider):
    """통합 호출: narrative fail → reflection 존재."""
    from services.agent.nodes.review import review_node

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None
    mock_compile.return_value = mock_compiled

    low_scores = {
        "hook": 0.2,
        "emotional_arc": 0.3,
        "twist_payoff": 0.1,
        "speaker_tone": 0.4,
        "script_image_sync": 0.3,
        "spoken_naturalness": 0.3,
        "retention_flow": 0.2,
        "pacing_rhythm": 0.2,
        "feedback": "Hook이 매우 약합니다.",
    }
    reflection_data = {
        "root_cause": "Hook 전략 부재",
        "impact": "시청자 이탈율 증가",
        "strategy": "씬 1에 질문형 Hook 추가",
        "expected_outcome": "시청 지속율 향상",
    }

    mock_llm_resp = MagicMock()
    mock_llm_resp.text = _make_unified_json(
        tech_passed=True,
        narrative_scores=low_scores,
        reflection=reflection_data,
    )
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)
    mock_llm_provider.return_value = mock_provider

    result = await review_node(_full_state())

    assert result["review_result"]["passed"] is False
    assert result["review_reflection"] is not None
    assert "Hook 전략 부재" in result["review_reflection"]
    assert "수정 전략" in result["review_reflection"]


@pytest.mark.asyncio
@patch("services.agent.nodes.review._legacy_evaluate", new_callable=AsyncMock)
@patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=(None, None))
async def test_unified_failure_falls_back_to_legacy(mock_unified, mock_legacy):
    """통합 호출 실패 → 레거시 폴백 동작 확인."""
    from services.agent.nodes.review import review_node

    mock_legacy.return_value = (None, None, None)

    result = await review_node(_full_state())

    assert mock_unified.called
    assert mock_legacy.called
    assert result["review_result"]["passed"] is True
