"""Research 노드 품질 점수 단위 테스트."""

from __future__ import annotations

import pytest

from services.agent.nodes.research_scoring import (
    _generate_feedback,
    _information_density,
    _source_diversity,
    _tool_success_rate,
    _topic_coverage,
    calculate_research_score,
)
from services.agent.state import ScriptState

# ── tool_success_rate ──────────────────────────────────────


def test_tool_success_rate_all_success():
    logs = [
        {"tool_name": "search_topic_history", "result": "[토픽 히스토리] 데이터 있음", "error": None},
        {"tool_name": "fetch_url_content", "result": "[URL 콘텐츠] 내용", "error": None},
    ]
    assert _tool_success_rate(logs) == 1.0


def test_tool_success_rate_partial_failure():
    logs = [
        {"tool_name": "search_topic_history", "result": "[토픽 히스토리] 데이터 있음", "error": None},
        {"tool_name": "fetch_url_content", "result": None, "error": "TimeoutError: connection failed"},
    ]
    assert _tool_success_rate(logs) == 0.5


def test_tool_success_rate_all_failure():
    logs = [
        {"tool_name": "search_topic_history", "result": None, "error": "Store error"},
        {"tool_name": "fetch_url_content", "result": None, "error": "Timeout"},
    ]
    assert _tool_success_rate(logs) == 0.0


def test_tool_success_rate_empty_logs():
    assert _tool_success_rate([]) == 0.0


def test_tool_success_rate_result_failure_keywords():
    """result에 실패 키워드('없음', '실패')가 포함되면 실패로 간주."""
    logs = [
        {
            "tool_name": "search_topic_history",
            "result": "[토픽 히스토리] '외로움'에 대한 과거 이력 없음",
            "error": None,
        },
        {"tool_name": "get_group_dna", "result": "[그룹 DNA] group_id=1의 채널 DNA 없음", "error": None},
    ]
    assert _tool_success_rate(logs) == 0.0


def test_tool_success_rate_excludes_trending():
    """analyze_trending은 제외."""
    logs = [
        {"tool_name": "search_topic_history", "result": "[토픽 히스토리] 데이터 있음", "error": None},
        {"tool_name": "analyze_trending", "result": "트렌딩 데이터", "error": None},
    ]
    # analyze_trending 제외 → 1개 중 1개 성공
    assert _tool_success_rate(logs) == 1.0


# ── information_density ────────────────────────────────────


@pytest.mark.parametrize(
    ("length", "expected_min", "expected_max"),
    [
        (0, 0.0, 0.0),
        (50, 0.2, 0.3),  # 50/100 * 0.5 = 0.25
        (100, 0.5, 0.5),  # 경계: 0.5
        (200, 0.6, 0.7),  # 0.5 + 0.5*(100/300) ≈ 0.667
        (400, 1.0, 1.0),
        (500, 1.0, 1.0),
    ],
)
def test_information_density_thresholds(length: int, expected_min: float, expected_max: float):
    brief = "x" * length
    score = _information_density(brief)
    assert expected_min <= score <= expected_max, f"length={length}, score={score}"


def test_information_density_none():
    assert _information_density(None) == 0.0


# ── source_diversity ───────────────────────────────────────


def test_source_diversity_calculation():
    logs = [
        {"tool_name": "search_topic_history"},
        {"tool_name": "fetch_url_content"},
        {"tool_name": "get_group_dna"},
    ]
    # 3 / 4 = 0.75
    assert _source_diversity(logs) == 0.75


def test_source_diversity_with_trending_excluded():
    logs = [
        {"tool_name": "search_topic_history"},
        {"tool_name": "analyze_trending"},  # 제외
    ]
    # 1 / 4 = 0.25
    assert _source_diversity(logs) == 0.25


def test_source_diversity_empty():
    assert _source_diversity([]) == 0.0


def test_source_diversity_all_tools():
    logs = [
        {"tool_name": "search_topic_history"},
        {"tool_name": "search_character_history"},
        {"tool_name": "fetch_url_content"},
        {"tool_name": "get_group_dna"},
    ]
    assert _source_diversity(logs) == 1.0


# ── topic_coverage ─────────────────────────────────────────


def test_topic_coverage_keyword_matching():
    state = ScriptState(topic="외로움 위로", character_id=None, group_id=None, references=None)
    brief = "외로움이라는 주제를 중심으로 위로의 감정을 전달합니다."
    score = _topic_coverage(brief, state)
    assert score == 1.0  # topic만 있고 매칭됨


def test_topic_coverage_with_all_signals():
    state = ScriptState(topic="외로움", character_id=1, group_id=2, references=["https://example.com"])
    brief = "외로움 주제의 캐릭터 히스토리를 분석한 결과, 그룹 채널 톤에 맞는 소재를 선택했습니다."
    score = _topic_coverage(brief, state)
    assert score == 1.0  # 4개 신호 모두 매칭


def test_topic_coverage_no_match():
    state = ScriptState(topic="외로움", character_id=1, group_id=None, references=None)
    brief = "이것은 관련 없는 내용입니다."
    score = _topic_coverage(brief, state)
    assert score < 0.5


def test_topic_coverage_no_brief():
    state = ScriptState(topic="외로움")
    assert _topic_coverage(None, state) == 0.0


def test_topic_coverage_no_signals():
    """topic도 없고 character/group/references도 없으면 중간값."""
    state = ScriptState(topic="")
    assert _topic_coverage("some brief", state) == 0.5


# ── overall + calculate_research_score ─────────────────────


def test_overall_weighted_calculation():
    state = ScriptState(topic="테스트 주제")
    logs = [
        {"tool_name": "search_topic_history", "result": "[토픽 히스토리] 데이터 있음", "error": None},
        {"tool_name": "fetch_url_content", "result": "[URL 콘텐츠] 상세 내용", "error": None},
    ]
    brief = "테스트 주제에 대한 상세한 리서치 결과입니다. " * 10  # ~200자

    score = calculate_research_score(state, logs, brief)
    assert score is not None
    assert 0.0 <= score["overall"] <= 1.0
    # 수동 검증: tool_success_rate=1.0, information_density≈0.67, source_diversity=0.5, topic_coverage=1.0
    expected = round(1.0 * 0.35 + score["information_density"] * 0.30 + 0.5 * 0.15 + 1.0 * 0.20, 3)
    assert score["overall"] == expected


def test_graceful_degradation_on_error(monkeypatch):
    """내부 예외 발생 시 None 반환."""
    monkeypatch.setattr(
        "services.agent.nodes.research_scoring._tool_success_rate",
        lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    state = ScriptState(topic="test")
    result = calculate_research_score(state, [], None)
    assert result is None


# ── generate_feedback ──────────────────────────────────────


def test_generate_feedback_all_good():
    scores = {
        "tool_success_rate": 0.8,
        "information_density": 0.6,
        "source_diversity": 0.5,
        "topic_coverage": 0.7,
    }
    assert _generate_feedback(scores) == "리서치 품질 양호"


def test_generate_feedback_all_low():
    scores = {
        "tool_success_rate": 0.2,
        "information_density": 0.1,
        "source_diversity": 0.1,
        "topic_coverage": 0.3,
    }
    feedback = _generate_feedback(scores)
    assert "도구 호출 성공률" in feedback
    assert "수집된 정보" in feedback
    assert "정보원 다양성" in feedback
    assert "주제 관련 정보" in feedback
