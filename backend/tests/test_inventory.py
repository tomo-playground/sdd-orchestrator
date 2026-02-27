"""Phase 20-A: inventory.py 단위 테스트.

DB 의존 함수는 mock으로 검증, 순수 함수는 직접 테스트.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from services.agent.inventory import (
    STRUCTURE_METADATA,
    CharacterSummary,
    StructureMeta,
    StyleSummary,
    _build_appearance_summary,
    load_structures,
)


class TestBuildAppearanceSummary:
    """_build_appearance_summary 태그 요약 로직."""

    def test_empty_tags(self):
        char = MagicMock()
        char.tags = []
        assert _build_appearance_summary(char) == ""

    def test_permanent_tags_only(self):
        tag1 = MagicMock()
        tag1.is_permanent = True
        tag1.tag = MagicMock()
        tag1.tag.name = "brown_hair"

        tag2 = MagicMock()
        tag2.is_permanent = False
        tag2.tag = MagicMock()
        tag2.tag.name = "smile"

        tag3 = MagicMock()
        tag3.is_permanent = True
        tag3.tag = MagicMock()
        tag3.tag.name = "blue_eyes"

        char = MagicMock()
        char.tags = [tag1, tag2, tag3]
        result = _build_appearance_summary(char)
        assert "brown_hair" in result
        assert "blue_eyes" in result
        assert "smile" not in result

    def test_max_10_tags(self):
        tags = []
        for i in range(15):
            t = MagicMock()
            t.is_permanent = True
            t.tag = MagicMock()
            t.tag.name = f"tag_{i}"
            tags.append(t)

        char = MagicMock()
        char.tags = tags
        result = _build_appearance_summary(char)
        assert result.count(",") <= 9  # 최대 10개

    def test_none_tags(self):
        char = MagicMock()
        char.tags = None
        assert _build_appearance_summary(char) == ""


class TestLoadStructures:
    """load_structures 인메모리 상수 반환."""

    def test_returns_four(self):
        result = load_structures()
        assert len(result) == 4

    def test_structure_ids(self):
        result = load_structures()
        ids = {s.id for s in result}
        assert ids == {"monologue", "dialogue", "narrated_dialogue", "confession"}

    def test_dialogue_requires_two(self):
        result = load_structures()
        dialogue = next(s for s in result if s.id == "dialogue")
        assert dialogue.requires_two_characters is True

    def test_monologue_single_char(self):
        result = load_structures()
        mono = next(s for s in result if s.id == "monologue")
        assert mono.requires_two_characters is False


class TestCharacterSummary:
    """CharacterSummary 데이터클래스."""

    def test_creation(self):
        cs = CharacterSummary(
            id=1,
            name="테스트",
            gender="female",
            appearance_summary="brown_hair, blue_eyes",
            has_lora=True,
            has_reference=False,
            usage_count=5,
        )
        assert cs.id == 1
        assert cs.has_lora is True
        assert cs.usage_count == 5

    def test_default_usage_count(self):
        cs = CharacterSummary(
            id=1,
            name="테스트",
            gender="male",
            appearance_summary="",
            has_lora=False,
            has_reference=False,
        )
        assert cs.usage_count == 0


class TestStructureMetadata:
    """STRUCTURE_METADATA 상수 검증."""

    def test_metadata_types(self):
        for s in STRUCTURE_METADATA:
            assert isinstance(s, StructureMeta)
            assert isinstance(s.id, str)
            assert isinstance(s.requires_two_characters, bool)

    def test_tones_are_set(self):
        for s in STRUCTURE_METADATA:
            assert len(s.tone) > 0


class TestStyleSummary:
    """StyleSummary 데이터클래스."""

    def test_creation(self):
        ss = StyleSummary(id=1, name="Anime", description="애니메이션 스타일")
        assert ss.id == 1
        assert ss.name == "Anime"
