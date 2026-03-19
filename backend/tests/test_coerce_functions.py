"""coerce_structure_id() / coerce_language_id() 단위 테스트.

Sprint A 과도기 핵심 함수: 다양한 형식의 입력을 snake_case ID로 정규화한다.
"""

from __future__ import annotations

import pytest

from config import (
    DEFAULT_LANGUAGE,
    DEFAULT_STRUCTURE,
    coerce_language_id,
    coerce_structure_id,
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
            ("confession", "confession"),
            # Title Case (DB 기존 데이터)
            ("Monologue", "monologue"),
            ("Dialogue", "dialogue"),
            ("Narrated Dialogue", "narrated_dialogue"),
            ("Confession", "confession"),
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
        for sid in ("monologue", "dialogue", "narrated_dialogue", "confession"):
            assert coerce_structure_id(coerce_structure_id(sid)) == sid


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
