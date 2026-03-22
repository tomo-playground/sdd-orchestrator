"""coerce_structure_id() / coerce_language_id() / coerce_tone_id() 단위 테스트.

Sprint A 과도기 핵심 함수: 다양한 형식의 입력을 snake_case ID로 정규화한다.
"""

from __future__ import annotations

import pytest

from config import (
    DEFAULT_LANGUAGE,
    DEFAULT_STRUCTURE,
    DEFAULT_TONE,
    coerce_language_id,
    coerce_structure_id,
    coerce_tone_id,
)

# ── coerce_structure_id ──────────────────────────────────────


class TestCoerceStructureId:
    """다양한 입력 형식에 대해 올바른 snake_case ID를 반환하는지 검증."""

    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            # snake_case ID (정규)
            ("monologue", "monologue"),
            ("dialogue", "dialogue"),
            ("narrated_dialogue", "narrated_dialogue"),
            # confession → monologue fallback (하위 호환)
            ("confession", "monologue"),
            # Title Case (DB 기존 데이터)
            ("Monologue", "monologue"),
            ("Dialogue", "dialogue"),
            ("Narrated Dialogue", "narrated_dialogue"),
            ("Confession", "monologue"),
            # Mixed case / underscore variants
            ("Narrated_Dialogue", "narrated_dialogue"),
            ("MONOLOGUE", "monologue"),
            ("DIALOGUE", "dialogue"),
            ("NARRATED_DIALOGUE", "narrated_dialogue"),
        ],
    )
    def test_known_values(self, input_val: str, expected: str):
        assert coerce_structure_id(input_val) == expected

    def test_none_returns_default(self):
        assert coerce_structure_id(None) == DEFAULT_STRUCTURE

    def test_empty_string_returns_default(self):
        assert coerce_structure_id("") == DEFAULT_STRUCTURE

    def test_whitespace_only_returns_default(self):
        assert coerce_structure_id("   ") == DEFAULT_STRUCTURE

    def test_unknown_value_returns_default(self):
        assert coerce_structure_id("unknown_structure") == DEFAULT_STRUCTURE

    def test_leading_trailing_whitespace_stripped(self):
        assert coerce_structure_id("  dialogue  ") == "dialogue"
        assert coerce_structure_id(" Narrated Dialogue ") == "narrated_dialogue"

    def test_idempotent(self):
        """이미 정규화된 값을 다시 coerce해도 동일."""
        for sid in ("monologue", "dialogue", "narrated_dialogue"):
            assert coerce_structure_id(coerce_structure_id(sid)) == sid


# ── coerce_tone_id ───────────────────────────────────────────


class TestCoerceToneId:
    """tone 문자열 정규화 검증."""

    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            ("intimate", "intimate"),
            ("emotional", "emotional"),
            ("dynamic", "dynamic"),
            ("humorous", "humorous"),
            ("suspense", "suspense"),
            ("INTIMATE", "intimate"),
            ("  emotional  ", "emotional"),
        ],
    )
    def test_known_values(self, input_val: str, expected: str):
        assert coerce_tone_id(input_val) == expected

    def test_none_returns_default(self):
        assert coerce_tone_id(None) == DEFAULT_TONE

    def test_empty_returns_default(self):
        assert coerce_tone_id("") == DEFAULT_TONE

    def test_whitespace_only_returns_default(self):
        assert coerce_tone_id("   ") == DEFAULT_TONE

    def test_unknown_returns_default(self):
        assert coerce_tone_id("invalid_tone") == DEFAULT_TONE

    def test_leading_trailing_whitespace_stripped(self):
        assert coerce_tone_id("  intimate  ") == "intimate"
        assert coerce_tone_id(" DYNAMIC ") == "dynamic"

    def test_idempotent(self):
        """이미 정규화된 값을 다시 coerce해도 동일."""
        for tid in ("intimate", "emotional", "dynamic", "humorous", "suspense"):
            assert coerce_tone_id(coerce_tone_id(tid)) == tid


# ── coerce_language_id ───────────────────────────────────────


class TestCoerceLanguageId:
    """다양한 입력 형식에 대해 올바른 lowercase ID를 반환하는지 검증."""

    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            # lowercase ID (정규)
            ("korean", "korean"),
            ("japanese", "japanese"),
            ("english", "english"),
            # Title Case (DB 기존 데이터)
            ("Korean", "korean"),
            ("Japanese", "japanese"),
            ("English", "english"),
            # UPPER CASE
            ("KOREAN", "korean"),
            ("JAPANESE", "japanese"),
            ("ENGLISH", "english"),
        ],
    )
    def test_known_values(self, input_val: str, expected: str):
        assert coerce_language_id(input_val) == expected

    def test_none_returns_default(self):
        assert coerce_language_id(None) == DEFAULT_LANGUAGE

    def test_empty_string_returns_default(self):
        assert coerce_language_id("") == DEFAULT_LANGUAGE

    def test_whitespace_only_returns_default(self):
        assert coerce_language_id("   ") == DEFAULT_LANGUAGE

    def test_unknown_value_returns_default(self):
        assert coerce_language_id("unknown_lang") == DEFAULT_LANGUAGE

    def test_leading_trailing_whitespace_stripped(self):
        assert coerce_language_id("  japanese  ") == "japanese"

    def test_idempotent(self):
        """이미 정규화된 값을 다시 coerce해도 동일."""
        for lid in ("korean", "japanese", "english"):
            assert coerce_language_id(coerce_language_id(lid)) == lid
