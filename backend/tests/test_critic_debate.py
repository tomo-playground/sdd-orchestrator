"""Critic 토론 테스트 (Phase 10-C-3)."""

from __future__ import annotations

import pytest

from services.agent.nodes._debate_utils import (
    _check_convergence,
    _concepts_too_similar,
    _estimate_hook_strength,
    _estimate_narrative_score,
)

# ── NarrativeScore 추정 테스트 ──────────────────────────────


def test_estimate_narrative_score_full():
    """완성도 높은 컨셉 → 높은 점수."""
    concept = {
        "title": "잃어버린 기억의 조각들",
        "concept": "어느 날 깨어났을 때, 나는 아무것도 기억하지 못했다. 단지 손에 쥔 사진 한 장뿐. 사진 속 웃고 있는 나와, 내 옆의 낯선 사람. 이 사람은 누구일까? 나는 왜 여기 있을까? 감동적인 진실이 기다린다.",
        "strengths": ["기억 상실", "사진 단서", "감정적 여정"],
    }
    score = _estimate_narrative_score(concept)
    assert score >= 0.7, f"Expected high score, got {score}"


def test_estimate_narrative_score_minimal():
    """최소 정보만 있는 컨셉 → 낮은 점수."""
    concept = {
        "title": "",
        "concept": "짧은 개요",
        "strengths": [],
    }
    score = _estimate_narrative_score(concept)
    assert score < 0.5, f"Expected low score, got {score}"


def test_estimate_narrative_score_empty():
    """빈 컨셉 → 0점."""
    concept = {}
    score = _estimate_narrative_score(concept)
    assert score == 0.0


# ── Hook 강도 추정 테스트 ──────────────────────────────────


def test_estimate_hook_strength_question():
    """질문형 Hook → 강한 점수."""
    concept = {"concept": "당신은 어떤 선택을 할 것인가? 생존을 위한 극한의 딜레마가 펼쳐진다."}
    strength = _estimate_hook_strength(concept)
    assert strength >= 0.3, f"Expected question bonus, got {strength}"


def test_estimate_hook_strength_shock():
    """충격형 Hook → 강한 점수."""
    concept = {"concept": "놀랍게도, 그 진실은 예상 밖이었다. 반전의 연속."}
    strength = _estimate_hook_strength(concept)
    assert strength >= 0.25, f"Expected shock bonus, got {strength}"


def test_estimate_hook_strength_weak():
    """일반 서술 → 약한 점수."""
    concept = {"concept": "평범한 일상 이야기입니다."}
    strength = _estimate_hook_strength(concept)
    assert strength < 0.3, f"Expected weak hook, got {strength}"


# ── Groupthink 감지 테스트 ─────────────────────────────────


def test_concepts_too_similar_yes():
    """유사한 컨셉들 → Groupthink."""
    concepts = [
        {"concept": "사랑과 이별의 이야기", "title": "사랑 이야기"},
        {"concept": "사랑과 이별의 감동", "title": "사랑 감동"},
        {"concept": "다른 주제", "title": "다른 것"},
    ]
    assert _concepts_too_similar(concepts, threshold=0.5), "Expected groupthink"


def test_concepts_too_similar_no():
    """다양한 컨셉들 → Groupthink 없음."""
    concepts = [
        {"concept": "우주 탐험의 신비", "title": "우주"},
        {"concept": "요리사의 꿈", "title": "요리"},
        {"concept": "음악의 힘", "title": "음악"},
    ]
    assert not _concepts_too_similar(concepts), "Expected diverse concepts"


def test_concepts_too_similar_empty():
    """빈 리스트 → Groupthink 없음."""
    assert not _concepts_too_similar([])


# ── 수렴 판단 테스트 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_check_convergence_high_score():
    """NarrativeScore 임계값 도달 → 수렴 (최소 라운드 충족 후)."""
    concepts = [
        {
            "title": "완성도 높은 컨셉",
            "concept": "어느 날 깨어났을 때, 나는 아무것도 기억하지 못했다. 놀라운 반전이 기다린다. 감동과 공포의 여정.",
            "strengths": ["기억 상실", "반전", "감정"],
        }
    ]
    messages = []
    # round_num=2: CONVERGENCE_MIN_ROUNDS(2) 충족
    converged = await _check_convergence(concepts, messages, round_num=2)
    assert converged, "Expected convergence on high score"


@pytest.mark.asyncio
async def test_check_convergence_max_rounds():
    """최대 라운드 도달 → 수렴."""
    concepts = [{"concept": "minimal", "strengths": []}]
    messages = []
    converged = await _check_convergence(concepts, messages, round_num=2)  # MAX_DEBATE_ROUNDS=2
    assert converged, "Expected convergence at max rounds"


@pytest.mark.asyncio
async def test_check_convergence_not_yet():
    """낮은 점수 + 초기 라운드 → 미수렴."""
    concepts = [{"concept": "짧은 개요", "strengths": []}]
    messages = []
    converged = await _check_convergence(concepts, messages, round_num=1)
    assert not converged, "Expected not converged yet"
