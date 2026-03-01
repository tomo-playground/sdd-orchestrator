"""Phase 20-A: inventory.py 단위 테스트.

DB 의존 함수는 mock으로 검증, 순수 함수는 직접 테스트.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.agent.inventory import (
    STRUCTURE_METADATA,
    CharacterSummary,
    StructureMeta,
    StyleSummary,
    _build_appearance_summary,
    _build_character_summary,
    load_characters,
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


class TestBuildCharacterSummary:
    """_build_character_summary 헬퍼."""

    def _make_char(self, **kwargs):
        char = MagicMock()
        char.id = kwargs.get("id", 1)
        char.name = kwargs.get("name", "테스트")
        char.gender = kwargs.get("gender", "female")
        char.tags = []
        char.loras = kwargs.get("loras", None)
        char.preview_image_asset_id = kwargs.get("preview_image_asset_id", None)
        return char

    def test_basic(self):
        char = self._make_char(id=5, name="소라", gender="female")
        result = _build_character_summary(char, count=3)
        assert result.id == 5
        assert result.name == "소라"
        assert result.usage_count == 3

    def test_has_lora_true(self):
        char = self._make_char(loras=[{"lora_id": 1}])
        result = _build_character_summary(char, count=0)
        assert result.has_lora is True

    def test_has_lora_false(self):
        char = self._make_char(loras=None)
        result = _build_character_summary(char, count=0)
        assert result.has_lora is False

    def test_has_reference_true(self):
        char = self._make_char(preview_image_asset_id=42)
        result = _build_character_summary(char, count=0)
        assert result.has_reference is True

    def test_has_reference_false(self):
        char = self._make_char(preview_image_asset_id=None)
        result = _build_character_summary(char, count=0)
        assert result.has_reference is False

    def test_unknown_gender_fallback(self):
        char = self._make_char(gender=None)
        result = _build_character_summary(char, count=0)
        assert result.gender == "unknown"


class TestLoadCharactersGroupFilter:
    """load_characters() group_id 필터링 로직."""

    def _make_summary(self, name: str, usage: int = 1) -> CharacterSummary:
        return CharacterSummary(
            id=1, name=name, gender="female",
            appearance_summary="", has_lora=False, has_reference=False,
            usage_count=usage,
        )

    def test_no_group_id_calls_all(self):
        """group_id=None이면 전체 캐릭터 반환."""
        db = MagicMock()
        all_chars = [self._make_summary("예민이", 69)]

        with patch("services.agent.inventory._load_all_characters", return_value=all_chars) as mock_all, \
             patch("services.agent.inventory._load_characters_for_group") as mock_group:
            result = load_characters(db, group_id=None)

        mock_all.assert_called_once()
        mock_group.assert_not_called()
        assert result == all_chars

    def test_group_id_returns_group_chars(self):
        """group_id 제공 시 그룹 캐릭터만 반환."""
        db = MagicMock()
        group_chars = [self._make_summary("소라", 2), self._make_summary("하나", 1)]

        with patch("services.agent.inventory._load_characters_for_group", return_value=group_chars) as mock_group, \
             patch("services.agent.inventory._load_all_characters") as mock_all:
            result = load_characters(db, group_id=12)

        mock_group.assert_called_once_with(db, 12, 20)
        mock_all.assert_not_called()
        assert result == group_chars

    def test_group_id_no_chars_falls_back_to_all(self):
        """그룹에 캐릭터 없으면 전체 폴백."""
        db = MagicMock()
        all_chars = [self._make_summary("예민이", 69)]

        with patch("services.agent.inventory._load_characters_for_group", return_value=[]), \
             patch("services.agent.inventory._load_all_characters", return_value=all_chars) as mock_all:
            result = load_characters(db, group_id=99)

        mock_all.assert_called_once()
        assert result == all_chars

    def test_group_chars_sorted_by_usage(self):
        """그룹 캐릭터는 usage_count 내림차순 정렬 유지."""
        db = MagicMock()
        group_chars = [
            self._make_summary("유카리", 2),
            self._make_summary("소라", 1),
            self._make_summary("하나", 1),
        ]

        with patch("services.agent.inventory._load_characters_for_group", return_value=group_chars):
            result = load_characters(db, group_id=12)

        assert result[0].name == "유카리"

    def test_max_count_passed_through(self):
        """max_count가 내부 함수로 전달됨."""
        db = MagicMock()

        with patch("services.agent.inventory._load_all_characters", return_value=[]) as mock_all:
            load_characters(db, group_id=None, max_count=5)

        mock_all.assert_called_once_with(db, 5)


class TestStyleSummary:
    """StyleSummary 데이터클래스."""

    def test_creation(self):
        ss = StyleSummary(id=1, name="Anime", description="애니메이션 스타일")
        assert ss.id == 1
        assert ss.name == "Anime"
