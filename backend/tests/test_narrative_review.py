"""Narrative Quality Foundation (Phase 9-5A) 테스트.

NarrativeScore 구조, Review 노드 서사 평가, Revise 피드백 주입,
라우팅 연동을 검증한다.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from services.agent.nodes.review import (
    _NARRATIVE_WEIGHTS,
    LANGGRAPH_NARRATIVE_THRESHOLD,
    _parse_narrative_score,
    review_node,
)
from services.agent.state import NarrativeScore, ScriptState


def _valid_scenes(count: int = 5) -> list[dict]:
    """Review 규칙 검증을 통과할 수 있는 유효한 씬 목록."""
    return [
        {
            "scene_id": i + 1,
            "script": f"테스트 씬 {i + 1}입니다 안녕하세요",
            "speaker": "A",
            "duration": 2,
            "image_prompt": "smile, looking_at_viewer, standing, indoors",
        }
        for i in range(count)
    ]


# --- 1. NarrativeScore 구조 검증 ---


def test_narrative_score_structure():
    """NarrativeScore TypedDict에 필요한 필드가 모두 존재한다."""
    score = NarrativeScore(
        hook=0.8,
        emotional_arc=0.7,
        twist_payoff=0.6,
        speaker_tone=0.9,
        script_image_sync=0.8,
        overall=0.75,
        feedback="훅이 강력합니다.",
    )
    assert score["hook"] == 0.8
    assert score["overall"] == 0.75
    assert "feedback" in score


# --- 2. Quick 모드 서사 평가 스킵 ---


@pytest.mark.asyncio
async def test_review_node_quick_mode_skips_narrative():
    """Quick 모드에서는 서사 품질 평가를 수행하지 않는다."""
    state: ScriptState = {
        "draft_scenes": _valid_scenes(),
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "skip_stages": ["research", "concept", "production", "explain"],
    }
    result = await review_node(state)
    review = result["review_result"]

    assert review["passed"] is True
    assert review.get("narrative_score") is None


# --- 3. Full 모드 + 규칙 통과 + 서사 통과 ---


@pytest.mark.asyncio
async def test_review_node_full_mode_narrative_pass():
    """Full 모드에서 규칙 통과 + 서사 점수 >= 임계값 → passed=True."""
    high_score = NarrativeScore(
        hook=0.9,
        emotional_arc=0.8,
        twist_payoff=0.7,
        speaker_tone=0.8,
        script_image_sync=0.9,
        overall=0.83,
        feedback="전체적으로 서사 품질이 우수합니다.",
    )

    state: ScriptState = {
        "draft_scenes": _valid_scenes(),
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "skip_stages": [],
    }
    with (
        patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=None),
        patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock, return_value=high_score),
    ):
        result = await review_node(state)
    review = result["review_result"]

    assert review["passed"] is True
    assert review.get("narrative_score") is not None
    assert review["narrative_score"]["overall"] >= LANGGRAPH_NARRATIVE_THRESHOLD


# --- 4. Full 모드 + 규칙 통과 + 서사 미달 ---


@pytest.mark.asyncio
async def test_review_node_full_mode_narrative_fail():
    """Full 모드에서 규칙 통과 + 서사 점수 < 임계값 → passed=False."""
    low_score = NarrativeScore(
        hook=0.2,
        emotional_arc=0.3,
        twist_payoff=0.1,
        speaker_tone=0.4,
        script_image_sync=0.5,
        overall=0.24,
        feedback="씬 1의 훅이 약합니다. 질문형 도입부를 사용하세요.",
    )

    state: ScriptState = {
        "draft_scenes": _valid_scenes(),
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "skip_stages": [],
    }
    with (
        patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=None),
        patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock, return_value=low_score),
    ):
        result = await review_node(state)
    review = result["review_result"]

    assert review["passed"] is False
    assert review["narrative_score"]["overall"] < LANGGRAPH_NARRATIVE_THRESHOLD
    assert "훅" in review["narrative_score"]["feedback"]


# --- 5. 규칙 실패 시 서사 평가 스킵 ---


@pytest.mark.asyncio
async def test_review_node_rule_fail_skips_narrative():
    """규칙 검증 실패 시 서사 품질 평가를 건너뛴다."""
    bad_scenes = [{"script": "짧", "speaker": "A", "duration": 0, "image_prompt": ""}]
    state: ScriptState = {
        "draft_scenes": bad_scenes,
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "skip_stages": [],
    }

    with (
        patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=None),
        patch("services.agent.nodes.review._gemini_evaluate", new_callable=AsyncMock, return_value=None),
    ):
        result = await review_node(state)

    review = result["review_result"]
    assert review["passed"] is False
    assert len(review["errors"]) > 0
    assert review.get("narrative_score") is None


# --- 6. Gemini 에러 시 graceful fallback ---


@pytest.mark.asyncio
async def test_narrative_evaluate_gemini_error_fallback():
    """Gemini API 에러 시 서사 평가 실패 → passed 유지 (graceful degradation)."""
    state: ScriptState = {
        "draft_scenes": _valid_scenes(),
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "topic": "테스트",
        "skip_stages": [],
    }
    with (
        patch("services.agent.nodes.review._unified_evaluate", new_callable=AsyncMock, return_value=None),
        patch("services.agent.nodes.review._narrative_evaluate", new_callable=AsyncMock, return_value=None),
    ):
        result = await review_node(state)
    review = result["review_result"]

    # Gemini 에러여도 규칙 통과했으므로 passed 유지
    assert review["passed"] is True
    assert review.get("narrative_score") is None


# --- 7. JSON 파싱 실패 시 fallback ---


def test_narrative_evaluate_parse_error_fallback():
    """잘못된 JSON 응답 시 _parse_narrative_score가 None을 반환한다."""
    assert _parse_narrative_score("이것은 JSON이 아닙니다") is None
    assert _parse_narrative_score("") is None
    assert _parse_narrative_score("{invalid json") is None


# --- 8. Revise 노드에서 narrative feedback 포함 ---


def test_revise_includes_narrative_feedback():
    """Revise의 _build_feedback()이 narrative feedback을 포함한다."""
    from services.agent.nodes.revise import _build_feedback

    state: ScriptState = {
        "topic": "테스트",
        "review_result": {
            "passed": False,
            "errors": [],
            "warnings": [],
            "narrative_score": {
                "overall": 0.4,
                "feedback": "씬 1 훅 개선 필요",
            },
        },
    }
    feedback = _build_feedback(state)
    assert "[서사 품질 피드백]" in feedback
    assert "씬 1 훅 개선 필요" in feedback


# --- 9. 서사 미달 → revise 라우팅 ---


def test_routing_narrative_fail_triggers_revise():
    """서사 점수 미달로 passed=False가 되면 route_after_review가 revise를 반환."""
    from services.agent.routing import route_after_review

    state: ScriptState = {
        "skip_stages": [],
        "review_result": {"passed": False, "errors": [], "warnings": []},
        "revision_count": 0,
    }
    assert route_after_review(state) == "revise"


# --- 10. 가중 평균 계산 검증 ---


def test_narrative_score_weights():
    """_parse_narrative_score가 가중 평균을 올바르게 계산한다."""
    raw = json.dumps(
        {
            "hook": 1.0,
            "emotional_arc": 1.0,
            "twist_payoff": 1.0,
            "speaker_tone": 1.0,
            "script_image_sync": 1.0,
            "feedback": "만점",
        }
    )
    score = _parse_narrative_score(raw)
    assert score is not None
    assert score["overall"] == 1.0

    # 가중치 합계 검증
    assert sum(_NARRATIVE_WEIGHTS.values()) == pytest.approx(1.0)

    # 부분 점수 검증
    raw_partial = json.dumps(
        {
            "hook": 0.5,
            "emotional_arc": 0.5,
            "twist_payoff": 0.5,
            "speaker_tone": 0.5,
            "script_image_sync": 0.5,
            "feedback": "중간",
        }
    )
    score_partial = _parse_narrative_score(raw_partial)
    assert score_partial is not None
    assert score_partial["overall"] == pytest.approx(0.5)

    # 마크다운 코드블록 래핑 처리
    raw_wrapped = f"```json\n{raw}\n```"
    score_wrapped = _parse_narrative_score(raw_wrapped)
    assert score_wrapped is not None
    assert score_wrapped["overall"] == 1.0
