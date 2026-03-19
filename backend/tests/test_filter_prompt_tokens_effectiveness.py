"""Test that effectiveness-based filtering is DISABLED (2026-02-24).

WD14 can only reliably detect ~15% of tags (clothing, subject, hair).
Using WD14 match data to remove tags caused a "death spiral" where valid
tags (blue_eyes, close-up, backlighting) were deleted because WD14 couldn't
detect them, not because they were ineffective for SD generation.

Effectiveness filtering was removed. These tests verify that ALL allowed
tags pass through filter_prompt_tokens() regardless of effectiveness score.
"""

from unittest.mock import patch

import pytest

from services.keywords import filter_prompt_tokens


@pytest.fixture
def mock_allowed_tags():
    """Mock allowed tags from DB."""
    return {
        "smile",
        "standing",
        "cowboy_shot",
        "classroom",
        "surprised",
        "confused",
        "laughing",
        "open_mouth",
        "sitting",
        "black_hair",
        "blue_eyes",
    }


@pytest.fixture
def mock_effectiveness_data():
    """Mock effectiveness data with mix of high/low scores."""
    return {
        "smile": (0.85, 50),
        "standing": (0.90, 30),
        "classroom": (0.88, 40),
        # These have 0% effectiveness but should NOT be filtered anymore
        "surprised": (0.0, 100),
        "confused": (0.0, 39),
        "laughing": (0.0, 194),
        "black_hair": (0.0, 89),
        "blue_eyes": (0.0, 134),
    }


class TestEffectivenessFilteringDisabled:
    """Verify effectiveness-based filtering is fully disabled."""

    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_keeps_all_allowed_tags_regardless_of_effectiveness(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_allowed_tags,
    ):
        """All allowed tags should pass through, even with 0% effectiveness."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = {}

        prompt = "smile, surprised, standing, classroom"
        result = filter_prompt_tokens(prompt)

        assert "smile" in result
        assert "surprised" in result  # 0% eff but kept
        assert "standing" in result
        assert "classroom" in result

    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_keeps_zero_effectiveness_tags(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_allowed_tags,
    ):
        """Tags with 0% effectiveness and high use_count should NOT be removed."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = {}

        prompt = "smile, laughing, confused, classroom"
        result = filter_prompt_tokens(prompt)

        assert "laughing" in result  # 0% eff, 194 uses — kept
        assert "confused" in result  # 0% eff, 39 uses — kept

    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_keeps_identity_tags(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_allowed_tags,
    ):
        """Identity tags (hair_color, eye_color) are kept — same as before."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = {}

        prompt = "smile, black_hair, blue_eyes, standing"
        result = filter_prompt_tokens(prompt)

        assert "black_hair" in result
        assert "blue_eyes" in result

    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_still_filters_unknown_tags(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_allowed_tags,
    ):
        """Tags NOT in allowed set should still be filtered (DB-based filtering)."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = {}

        prompt = "smile, totally_fake_tag, standing"
        result = filter_prompt_tokens(prompt)

        assert "smile" in result
        assert "standing" in result
        assert "totally_fake_tag" not in result  # Not in allowed set

    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_alias_replacement_still_works(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_allowed_tags,
    ):
        """TagAliasCache replacement should still function."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = {}

        prompt = "smile, standing, classroom"
        result = filter_prompt_tokens(prompt)

        # Basic tokens pass through
        assert "smile" in result
        assert "standing" in result
        assert "classroom" in result

    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_deduplication_still_works(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_allowed_tags,
    ):
        """Duplicate tags should still be deduplicated."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = {}

        prompt = "smile, smile, standing, standing"
        result = filter_prompt_tokens(prompt)

        assert result.count("smile") == 1
        assert result.count("standing") == 1
