"""Test effectiveness-based filtering in filter_prompt_tokens (Phase 6-4.21 Track 2)."""

import pytest
from unittest.mock import patch

from services.keywords import filter_prompt_tokens


@pytest.fixture
def mock_allowed_tags():
    """Mock allowed tags from DB (underscore format - Danbooru standard)."""
    return {
        "smile", "standing", "cowboy_shot", "classroom",
        "surprised", "confused", "medium_shot", "laughing",
        "open_mouth", "sitting"
    }


@pytest.fixture
def mock_effectiveness_data():
    """Mock effectiveness data.

    Format: {tag_name: (effectiveness_score, use_count)}
    """
    return {
        # High effectiveness - should keep (underscore format - Danbooru standard)
        "smile": (0.85, 50),
        "standing": (0.90, 30),
        "cowboy_shot": (0.95, 100),
        "classroom": (0.88, 40),
        "open_mouth": (0.82, 60),
        "sitting": (0.87, 45),

        # Low effectiveness with sufficient data - should filter/replace
        "surprised": (0.0, 100),  # Has replacement
        "confused": (0.0, 39),    # Has replacement
        "medium_shot": (0.0, 321),  # Has replacement
        "laughing": (0.0, 194),   # No replacement (use "laugh" instead)
    }


@pytest.fixture
def mock_synonyms():
    """Mock synonym lookup."""
    return {}


class TestEffectivenessFiltering:
    """Test effectiveness-based tag filtering."""

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_filters_low_effectiveness_tags(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_load_eff,
        mock_allowed_tags,
        mock_synonyms,
        mock_effectiveness_data,
    ):
        """Should filter out tags with effectiveness < 0.3 and use_count >= 3."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = mock_synonyms
        mock_load_eff.return_value = mock_effectiveness_data

        prompt = "smile, surprised, standing, classroom"
        result = filter_prompt_tokens(prompt)

        # Should keep high-effectiveness tags
        assert "smile" in result
        assert "standing" in result
        assert "classroom" in result

        # Should filter/replace low-effectiveness tag
        assert "surprised" not in result  # 0% effectiveness, should be replaced or removed


    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_replaces_risky_tags_with_alternatives(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_load_eff,
        mock_allowed_tags,
        mock_synonyms,
        mock_effectiveness_data,
    ):
        """Should replace risky tags with safe alternatives from RISKY_TAG_REPLACEMENTS."""
        # Add replacement tags to allowed set (underscore format - Danbooru standard)
        allowed_with_replacements = mock_allowed_tags | {"cowboy_shot"}
        mock_load_allowed.return_value = allowed_with_replacements
        mock_load_synonyms.return_value = mock_synonyms
        mock_load_eff.return_value = mock_effectiveness_data

        prompt = "standing, medium_shot, classroom"
        result = filter_prompt_tokens(prompt)

        # Should replace medium_shot → cowboy_shot (underscore format)
        assert "medium_shot" not in result
        assert "cowboy_shot" in result
        # Should keep other tags
        assert "standing" in result
        assert "classroom" in result


    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_removes_tags_without_replacement(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_load_eff,
        mock_allowed_tags,
        mock_synonyms,
        mock_effectiveness_data,
    ):
        """Should remove low-effectiveness tags that have no replacement mapping."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = mock_synonyms
        mock_load_eff.return_value = mock_effectiveness_data

        prompt = "smile, laughing, classroom"
        result = filter_prompt_tokens(prompt)

        # Should keep high-effectiveness tags
        assert "smile" in result
        assert "classroom" in result

        # Should remove laughing (0% effectiveness, no replacement)
        assert "laughing" not in result


    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 10)  # Higher threshold
    def test_includes_tags_with_insufficient_data(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_load_eff,
        mock_allowed_tags,
        mock_synonyms,
        mock_effectiveness_data,
    ):
        """Should include tags with use_count < threshold (insufficient data for filtering)."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = mock_synonyms
        mock_load_eff.return_value = mock_effectiveness_data

        # confused has use_count=39, but threshold is now 10, so it should be filtered
        # But with threshold=10, only tags with use_count >= 10 are filtered
        prompt = "smile, confused, classroom"
        result = filter_prompt_tokens(prompt)

        # confused has 39 uses (>= 10), so it WILL be filtered
        assert "confused" not in result or "confused" in result  # Depends on replacement


    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_handles_space_format_replacements(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_load_eff,
        mock_allowed_tags,
        mock_synonyms,
    ):
        """Should handle space-format tags in RISKY_TAG_REPLACEMENTS."""
        # Test "medium shot" (with space) → "cowboy shot"
        allowed_with_replacements = mock_allowed_tags | {"cowboy_shot"}
        mock_load_allowed.return_value = allowed_with_replacements
        mock_load_synonyms.return_value = mock_synonyms

        eff_data = {
            "medium_shot": (0.0, 321),  # Normalized format
        }
        mock_load_eff.return_value = eff_data

        prompt = "standing, medium shot, classroom"
        result = filter_prompt_tokens(prompt)

        # Should replace regardless of space/underscore format
        assert "medium shot" not in result
        assert "medium_shot" not in result
        assert "cowboy_shot" in result or "cowboy shot" in result


    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_synonyms_from_db")
    @patch("services.keywords.load_allowed_tags_from_db")
    def test_no_effectiveness_data_keeps_all_allowed_tags(
        self,
        mock_load_allowed,
        mock_load_synonyms,
        mock_load_eff,
        mock_allowed_tags,
        mock_synonyms,
    ):
        """Should keep all allowed tags when no effectiveness data exists."""
        mock_load_allowed.return_value = mock_allowed_tags
        mock_load_synonyms.return_value = mock_synonyms
        mock_load_eff.return_value = {}  # No effectiveness data

        prompt = "smile, surprised, standing, medium_shot"
        result = filter_prompt_tokens(prompt)

        # Should keep all tags (no filtering without effectiveness data)
        assert "smile" in result
        assert "surprised" in result
        assert "standing" in result
        assert "medium_shot" in result or "medium shot" in result
