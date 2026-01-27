"""Test cases for format_keyword_context function.

Validates tag effectiveness filtering and Gemini prompt formatting.
"""

import pytest
from unittest.mock import patch

from services.keywords import format_keyword_context


@pytest.fixture
def mock_db_tags():
    """Mock tag database with various groups."""
    return {
        "expression": ["smile", "crying", "neutral"],
        "pose": ["standing", "sitting", "running"],
        "camera": ["cowboy shot", "close-up", "full body"],
        "location_indoor": ["classroom", "bedroom"],
    }


@pytest.fixture
def mock_effectiveness_data():
    """Mock tag effectiveness data.

    Format: {tag_name: (effectiveness_score, use_count)}
    """
    return {
        "smile": (0.85, 10),  # High effectiveness, sufficient data
        "crying": (0.25, 8),  # Low effectiveness, sufficient data (should be filtered)
        "neutral": (0.60, 2),  # Medium effectiveness, insufficient data (should be included)
        "standing": (0.90, 15),  # Very high effectiveness
        "sitting": (None, 5),  # No effectiveness data yet (should be included)
        "running": (0.40, 1),  # Medium-low effectiveness, insufficient data
        "cowboy shot": (0.95, 20),  # Excellent effectiveness
        "close-up": (0.70, 10),  # Good effectiveness
        "full body": (0.28, 12),  # Low effectiveness, sufficient data (should be filtered)
        "classroom": (0.88, 18),  # High effectiveness
        "bedroom": (0.75, 9),  # Good effectiveness
    }


class TestBasicFormatting:
    """Test basic formatting without effectiveness filtering."""

    @patch("services.keywords.load_tags_from_db")
    def test_no_filtering(self, mock_load_tags, mock_db_tags):
        """Should return all tags when filtering is disabled."""
        mock_load_tags.return_value = mock_db_tags

        result = format_keyword_context(filter_by_effectiveness=False)

        # Should include header
        assert "Allowed Keywords (use exactly as written):" in result
        # Should include all categories
        assert "expression:" in result.lower()
        assert "pose:" in result.lower()
        assert ("camera" in result.lower() or "shot_type" in result.lower())
        # Should include all tags
        assert "smile" in result
        assert "crying" in result
        assert "neutral" in result

    @patch("services.keywords.load_tags_from_db")
    def test_empty_database(self, mock_load_tags):
        """Should return empty string when no tags in database."""
        mock_load_tags.return_value = {}

        result = format_keyword_context()

        assert result == ""


class TestEffectivenessFiltering:
    """Test effectiveness-based tag filtering."""

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_filters_low_effectiveness_tags(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should exclude tags with effectiveness < threshold and sufficient data."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should include high-effectiveness tags
        assert "smile" in result
        assert "standing" in result
        assert "cowboy shot" in result
        assert "classroom" in result

        # Should exclude low-effectiveness tags with sufficient data
        assert "crying" not in result  # 0.25 effectiveness, 8 uses
        assert "full body" not in result  # 0.28 effectiveness, 12 uses

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_includes_insufficient_data_tags(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should include tags with use_count < threshold (needs testing)."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should include tags with insufficient data (< 3 uses)
        assert "neutral" in result  # 0.60 effectiveness, 2 uses
        assert "running" in result  # 0.40 effectiveness, 1 use

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_includes_no_effectiveness_data_tags(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should include tags with no effectiveness data yet."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should include tags with no effectiveness data
        assert "sitting" in result  # None effectiveness, 5 uses

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_includes_unknown_tags(
        self, mock_load_tags, mock_load_eff, mock_db_tags
    ):
        """Should include tags not in effectiveness map (new tags)."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = {}  # Empty effectiveness map

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should include all tags (all are unknown/new)
        assert "smile" in result
        assert "crying" in result
        assert "standing" in result


class TestSortingBehavior:
    """Test that tags are sorted by effectiveness."""

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_sorts_by_effectiveness_descending(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should sort tags by effectiveness (high to low) within each category."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # Find expression line in Allowed Keywords section (not Recommended section)
        lines = result.split("\n")
        allowed_idx = next(i for i, line in enumerate(lines) if "Allowed Keywords" in line)
        expr_line = next(
            line for line in lines[allowed_idx:] if "expression:" in line.lower()
        )

        # smile (0.85) should appear before neutral (0.60, but insufficient data = 0.5 default)
        smile_pos = expr_line.index("smile")
        neutral_pos = expr_line.index("neutral")
        assert smile_pos < neutral_pos, "High-effectiveness tags should appear first"


class TestCategoryMapping:
    """Test that DB groups are correctly mapped to Gemini categories."""

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    def test_maps_indoor_to_environment(
        self, mock_load_tags, mock_load_eff, mock_db_tags
    ):
        """Should map location_indoor to environment category."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = {}

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should use Gemini-friendly category name
        assert "environment:" in result.lower() or "location:" in result.lower()
        assert "classroom" in result


class TestConfigurableThresholds:
    """Test that config thresholds are respected."""

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.5)  # Higher threshold
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    def test_respects_custom_effectiveness_threshold(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should use TAG_EFFECTIVENESS_THRESHOLD from config."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # With threshold=0.5, should exclude tags with 0.4 effectiveness
        assert "classroom" in result  # 0.88
        assert "standing" in result  # 0.90
        # crying (0.25) and neutral (0.40) should be excluded
        # But neutral has use_count=2 < 3, so it's included anyway
        assert "neutral" in result  # Insufficient data

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 10)  # Higher min count
    def test_respects_custom_min_use_count(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should use TAG_MIN_USE_COUNT_FOR_FILTERING from config."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # With min_use_count=10, tags with < 10 uses should be included regardless
        assert "crying" in result  # 0.25 effectiveness, but only 8 uses
        assert "neutral" in result  # 0.60 effectiveness, only 2 uses


class TestRecommendedTagsSection:
    """Test recommended high-performance tags section (Phase 6-4-21 Task #8)."""

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    @patch("config.RECOMMENDATION_EFFECTIVENESS_THRESHOLD", 0.8)
    @patch("config.RECOMMENDATION_MIN_USE_COUNT", 10)
    def test_includes_recommended_tags_section(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should include 'Recommended High-Performance Tags' section."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should include recommended section header
        assert "Recommended High-Performance Tags" in result
        assert "proven >80% effectiveness" in result

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    @patch("config.RECOMMENDATION_EFFECTIVENESS_THRESHOLD", 0.8)
    @patch("config.RECOMMENDATION_MIN_USE_COUNT", 10)
    def test_recommended_tags_meet_threshold(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Should only recommend tags with effectiveness >= 0.8 and use_count >= 10."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)
        lines = result.split("\n")

        # Find recommended section
        rec_start = next(i for i, line in enumerate(lines) if "Recommended" in line)
        rec_end = next(
            (i for i, line in enumerate(lines[rec_start:], rec_start) if line == ""),
            len(lines)
        )
        rec_section = "\n".join(lines[rec_start:rec_end])

        # Should include high-effectiveness tags (>= 0.8, >= 10 uses)
        assert "smile" in rec_section  # 0.85, 10 uses
        assert "standing" in rec_section  # 0.90, 15 uses
        assert "cowboy shot" in rec_section  # 0.95, 20 uses
        assert "classroom" in rec_section  # 0.88, 18 uses

        # Should NOT include tags below threshold
        assert "close-up" not in rec_section  # 0.70 < 0.8
        assert "bedroom" not in rec_section  # 0.75 < 0.8
        assert "neutral" not in rec_section  # 0.60 < 0.8, insufficient uses

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    @patch("config.RECOMMENDATION_EFFECTIVENESS_THRESHOLD", 0.8)
    @patch("config.RECOMMENDATION_MIN_USE_COUNT", 10)
    def test_recommended_section_before_allowed_keywords(
        self, mock_load_tags, mock_load_eff, mock_db_tags, mock_effectiveness_data
    ):
        """Recommended section should appear before Allowed Keywords section."""
        mock_load_tags.return_value = mock_db_tags
        mock_load_eff.return_value = mock_effectiveness_data

        result = format_keyword_context(filter_by_effectiveness=True)

        rec_pos = result.index("Recommended High-Performance Tags")
        allowed_pos = result.index("Allowed Keywords")

        assert rec_pos < allowed_pos, "Recommended section should appear first"

    @patch("services.keywords.load_tag_effectiveness_map")
    @patch("services.keywords.load_tags_from_db")
    @patch("config.TAG_EFFECTIVENESS_THRESHOLD", 0.3)
    @patch("config.TAG_MIN_USE_COUNT_FOR_FILTERING", 3)
    @patch("config.RECOMMENDATION_EFFECTIVENESS_THRESHOLD", 0.8)
    @patch("config.RECOMMENDATION_MIN_USE_COUNT", 10)
    def test_no_recommended_section_when_no_qualifying_tags(
        self, mock_load_tags, mock_load_eff
    ):
        """Should not include recommended section if no tags qualify."""
        # Tags with low effectiveness or insufficient data
        mock_load_tags.return_value = {
            "expression": ["smile", "frown"],
        }
        mock_load_eff.return_value = {
            "smile": (0.70, 15),  # Below threshold
            "frown": (0.85, 5),   # Below min use count
        }

        result = format_keyword_context(filter_by_effectiveness=True)

        # Should not include recommended section
        assert "Recommended High-Performance Tags" not in result
        # Should still include Allowed Keywords section
        assert "Allowed Keywords" in result
        assert "smile" in result
        assert "frown" in result
