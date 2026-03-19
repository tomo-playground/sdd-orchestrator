"""POST /scripts/analyze-topic 토픽 분석 단위 테스트.

_validate_topic_analysis()의 post-validation 로직을 검증한다.
캐릭터 캐스팅은 Director 노드가 담당하므로 여기서는 duration/structure/language만 검증.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def validate():
    from services.scripts.topic_analysis import _validate_topic_analysis  # noqa: PLC0415

    def _run(parsed: dict):
        return _validate_topic_analysis(parsed)

    return _run


# ── Duration 검증 ──


def test_valid_duration(validate):
    """허용 목록 내 duration은 그대로 반환."""
    result = validate({"duration": 45})
    assert result["duration"] == 45


def test_invalid_duration_fallback(validate):
    """허용 목록 외 duration은 30초로 대체."""
    result = validate({"duration": 99})
    assert result["duration"] == 30


def test_missing_duration_default(validate):
    """duration 미지정 시 기본값 30초."""
    result = validate({})
    assert result["duration"] == 30


# ── Structure 검증 ──


def test_valid_structure(validate):
    """유효한 structure는 capitalized name으로 반환."""
    result = validate({"structure": "dialogue"})
    assert result["structure"] == "dialogue"


def test_valid_structure_case_insensitive(validate):
    """대소문자 구분 없이 매칭."""
    result = validate({"structure": "Narrated_Dialogue"})
    assert result["structure"] == "narrated_dialogue"


def test_invalid_structure_fallback(validate):
    """유효하지 않은 structure는 Monologue로 대체."""
    result = validate({"structure": "unknown_structure"})
    assert result["structure"] == "monologue"


# ── Language 검증 ──


def test_valid_language(validate):
    """유효한 language는 그대로 반환."""
    result = validate({"language": "Japanese"})
    assert result["language"] == "japanese"


def test_invalid_language_fallback(validate):
    """유효하지 않은 language는 Korean으로 대체."""
    result = validate({"language": "Chinese"})
    assert result["language"] == "korean"


# ── 전체 결과 필드 확인 ──


def test_full_result_has_all_fields(validate):
    """결과에 필수 4개 필드가 포함된다."""
    result = validate({"duration": 30, "language": "Korean", "structure": "monologue"})
    expected_keys = {"duration", "language", "structure", "reasoning"}
    assert expected_keys.issubset(set(result.keys()))
    assert result["structure"] == "monologue"
