"""POST /scripts/analyze-topic 토픽 분석 단위 테스트.

_validate_topic_analysis()의 post-validation 로직을 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class FakeCharacter:
    id: int
    name: str


# _validate_topic_analysis에 넘길 characters mock
CHARS = [FakeCharacter(id=1, name="유나"), FakeCharacter(id=2, name="하루")]


@pytest.fixture
def validate():
    from services.scripts.topic_analysis import _validate_topic_analysis  # noqa: PLC0415

    def _run(parsed: dict, characters=None):
        return _validate_topic_analysis(parsed, CHARS if characters is None else characters)

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
    assert result["structure"] == "Dialogue"


def test_valid_structure_case_insensitive(validate):
    """대소문자 구분 없이 매칭."""
    result = validate({"structure": "Narrated_Dialogue"})
    assert result["structure"] == "Narrated Dialogue"


def test_invalid_structure_fallback(validate):
    """유효하지 않은 structure는 Monologue로 대체."""
    result = validate({"structure": "unknown_structure"})
    assert result["structure"] == "Monologue"


# ── Language 검증 ──


def test_valid_language(validate):
    """유효한 language는 그대로 반환."""
    result = validate({"language": "Japanese"})
    assert result["language"] == "Japanese"


def test_invalid_language_fallback(validate):
    """유효하지 않은 language는 Korean으로 대체."""
    result = validate({"language": "Chinese"})
    assert result["language"] == "Korean"


# ── Character 검증 ──


def test_valid_character(validate):
    """존재하는 character_a_id는 이름이 DB 값으로 교정된다."""
    result = validate({"character_a_id": 1, "character_a_name": "wrong_name"})
    assert result["character_a_id"] == 1
    assert result["character_a_name"] == "유나"


def test_invalid_character_cleared(validate):
    """존재하지 않는 character_a_id는 null로 대체."""
    result = validate({"character_a_id": 999, "character_a_name": "없는캐릭"})
    assert result["character_a_id"] is None
    assert result["character_a_name"] is None


def test_character_b_valid(validate):
    """존재하는 character_b_id는 이름이 교정된다."""
    result = validate({"character_b_id": 2, "character_b_name": "wrong"})
    assert result["character_b_id"] == 2
    assert result["character_b_name"] == "하루"


def test_character_b_invalid_cleared(validate):
    """존재하지 않는 character_b_id는 null로 대체."""
    result = validate({"character_b_id": 999})
    assert result["character_b_id"] is None
    assert result["character_b_name"] is None


def test_no_characters_available(validate):
    """캐릭터 목록이 비었을 때 character_a_id가 null로 처리."""
    result = validate({"character_a_id": 1}, characters=[])
    assert result["character_a_id"] is None


# ── 전체 결과 필드 확인 ──


def test_character_name_cleared_when_id_none(validate):
    """character_a_id가 None이면 character_name도 반드시 None."""
    result = validate({"character_a_id": None, "character_a_name": "유령이름"})
    assert result["character_a_id"] is None
    assert result["character_a_name"] is None


def test_full_result_has_all_fields(validate):
    """결과에 필수 8개 필드가 포함된다."""
    result = validate({"duration": 30, "language": "Korean", "structure": "monologue"})
    expected_keys = {
        "duration",
        "language",
        "structure",
        "character_a_id",
        "character_a_name",
        "character_b_id",
        "character_b_name",
        "reasoning",
    }
    assert expected_keys.issubset(set(result.keys()))
    assert result["structure"] == "Monologue"


# ── Character ID 타입 변환 검증 (Event loop / Gemini 응답 방어) ──


def test_character_a_id_string_coerced_to_int(validate):
    """Gemini가 character_a_id를 문자열로 반환해도 int 변환 후 매칭."""
    result = validate({"character_a_id": "1"})
    assert result["character_a_id"] == 1
    assert result["character_a_name"] == "유나"


def test_character_b_id_string_coerced(validate):
    """character_b_id 문자열도 int 변환."""
    result = validate({"character_b_id": "2"})
    assert result["character_b_id"] == 2
    assert result["character_b_name"] == "하루"


def test_character_a_id_float_coerced(validate):
    """Gemini가 float(1.0)을 반환해도 int로 변환."""
    result = validate({"character_a_id": 1.0})
    assert result["character_a_id"] == 1
    assert result["character_a_name"] == "유나"


def test_character_a_id_invalid_string_cleared(validate):
    """변환 불가능한 문자열은 None으로 처리."""
    result = validate({"character_a_id": "unknown"})
    assert result["character_a_id"] is None


def test_character_a_id_zero_cleared(validate):
    """character_a_id=0은 falsy이므로 None처럼 처리되어야 한다."""
    result = validate({"character_a_id": 0})
    assert result["character_a_id"] is None


def test_character_a_id_hallucinated_not_in_group(validate):
    """Gemini가 존재하지 않는 ID(999)를 반환하면 None."""
    result = validate({"character_a_id": 999, "character_b_id": 888})
    assert result["character_a_id"] is None
    assert result["character_b_id"] is None


def test_empty_characters_with_string_id(validate):
    """캐릭터 목록 비어있으면 어떤 ID도 매칭 불가."""
    result = validate({"character_a_id": "1"}, characters=[])
    assert result["character_a_id"] is None
