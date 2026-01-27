"""Test cases for tag normalization and compound adjective fixing.

Validates that Gemini-generated prompts are correctly normalized for SD compatibility.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.prompt import (
    fix_compound_adjectives,
    normalize_and_fix_tags,
    normalize_tag_spaces,
    validate_tags_with_danbooru,
)


class TestNormalizeTagSpaces:
    """Test space-to-underscore normalization."""

    @pytest.mark.parametrize(
        "input_tags,expected",
        [
            # Basic space normalization
            (["thumbs up"], ["thumbs_up"]),
            (["looking at viewer"], ["looking_at_viewer"]),
            (["full body"], ["full_body"]),
            # Multiple tags
            (["thumbs up", "smiling"], ["thumbs_up", "smiling"]),
            # Already normalized (no change)
            (["thumbs_up"], ["thumbs_up"]),
            (["green_hair"], ["green_hair"]),
            # Mixed spaces and underscores
            (["looking at viewer", "green_hair"], ["looking_at_viewer", "green_hair"]),
            # Extra whitespace handling
            (["  thumbs up  "], ["thumbs_up"]),
            (["  looking  at  viewer  "], ["looking__at__viewer"]),
        ],
    )
    def test_space_to_underscore(self, input_tags, expected):
        """Should convert all spaces to underscores."""
        result = normalize_tag_spaces(input_tags)
        assert result == expected

    def test_empty_list(self):
        """Should handle empty list."""
        assert normalize_tag_spaces([]) == []

    def test_single_word_tags(self):
        """Should not modify single-word tags."""
        input_tags = ["smile", "standing", "outdoors"]
        result = normalize_tag_spaces(input_tags)
        assert result == input_tags


class TestFixCompoundAdjectives:
    """Test compound adjective pattern detection and splitting."""

    @pytest.mark.parametrize(
        "input_tags,expected",
        [
            # Hair compounds
            (["short_green_hair"], ["short_hair", "green_hair"]),
            (["long_blonde_hair"], ["long_hair", "blonde_hair"]),
            (["medium_blue_hair"], ["medium_hair", "blue_hair"]),
            # Clothing compounds
            (["white_blue_dress"], ["white_dress", "blue_dress"]),
            (["black_red_shirt"], ["black_shirt", "red_shirt"]),
            (["green_yellow_shorts"], ["green_shorts", "yellow_shorts"]),
            # Accessory compounds
            (["black_white_ribbon"], ["black_ribbon", "white_ribbon"]),
            (["red_blue_bow"], ["red_bow", "blue_bow"]),
            # Non-matching patterns (no change)
            (["green_hair"], ["green_hair"]),
            (["white_dress"], ["white_dress"]),
            (["smile"], ["smile"]),
            # Multiple tags mixed
            (
                ["short_green_hair", "smile", "white_blue_dress"],
                ["short_hair", "green_hair", "smile", "white_dress", "blue_dress"],
            ),
        ],
    )
    def test_compound_splitting(self, input_tags, expected):
        """Should split compound adjectives into separate tags."""
        result = fix_compound_adjectives(input_tags)
        assert result == expected

    def test_preserves_valid_tags(self):
        """Should not modify tags that don't match patterns."""
        input_tags = ["smile", "standing", "outdoors", "green_hair", "white_dress"]
        result = fix_compound_adjectives(input_tags)
        assert result == input_tags

    def test_empty_list(self):
        """Should handle empty list."""
        assert fix_compound_adjectives([]) == []


class TestNormalizeAndFixTags:
    """Test full pipeline: spaces + compound fixing."""

    @pytest.mark.parametrize(
        "input_prompt,expected",
        [
            # Real-world problematic case from Scene 2
            (
                "short green hair, thumbs up, smiling",
                "short_hair, green_hair, thumbs_up, smiling",
            ),
            # Complex multi-issue prompt
            (
                "long blonde hair, looking at viewer, white blue dress",
                "long_hair, blonde_hair, looking_at_viewer, white_dress, blue_dress",
            ),
            # Already valid prompt (minimal changes)
            ("green_hair, smile, standing", "green_hair, smile, standing"),
            # Mixed valid and invalid
            (
                "medium red hair, full body, black white ribbon",
                "medium_hair, red_hair, full_body, black_ribbon, white_ribbon",
            ),
            # Edge case: empty prompt
            ("", ""),
            ("   ", ""),
            # Single tag
            ("thumbs up", "thumbs_up"),
            ("short green hair", "short_hair, green_hair"),
        ],
    )
    def test_full_pipeline(self, input_prompt, expected):
        """Should normalize spaces and fix compounds in one pass."""
        result = normalize_and_fix_tags(input_prompt)
        assert result == expected

    def test_preserves_order(self):
        """Should maintain tag order."""
        input_prompt = "smile, short green hair, standing, thumbs up"
        result = normalize_and_fix_tags(input_prompt)
        # smile first, then hair tags, then standing, then thumbs_up
        tags = [t.strip() for t in result.split(",")]
        assert tags[0] == "smile"
        assert "standing" in tags
        assert tags[-1] == "thumbs_up"

    def test_removes_empty_tags(self):
        """Should filter out empty tags from split."""
        input_prompt = "smile,  , standing, , thumbs up"
        result = normalize_and_fix_tags(input_prompt)
        tags = [t.strip() for t in result.split(",")]
        assert "" not in tags
        assert len(tags) == 3  # smile, standing, thumbs_up


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_input(self):
        """Should handle None gracefully."""
        # normalize_tag_spaces expects list, but normalize_and_fix_tags handles string
        assert normalize_and_fix_tags("") == ""

    def test_very_long_prompt(self):
        """Should handle prompts with many tags."""
        tags = [
            "smile",
            "short green hair",
            "standing",
            "thumbs up",
            "looking at viewer",
            "white blue dress",
            "outdoors",
            "sunny",
            "full body",
        ]
        input_prompt = ", ".join(tags)
        result = normalize_and_fix_tags(input_prompt)
        # Should contain all base tags
        assert "smile" in result
        assert "standing" in result
        assert "outdoors" in result
        # Should fix compounds
        assert "short_hair" in result
        assert "green_hair" in result
        assert "thumbs_up" in result
        assert "white_dress" in result
        assert "blue_dress" in result

    def test_unicode_tags(self):
        """Should handle non-ASCII characters (though rare in SD tags)."""
        input_prompt = "smile, standing"  # Basic ASCII
        result = normalize_and_fix_tags(input_prompt)
        assert result == "smile, standing"

    def test_special_characters(self):
        """Should handle underscores in original tags."""
        input_prompt = "1girl, solo, green_hair"
        result = normalize_and_fix_tags(input_prompt)
        assert result == "1girl, solo, green_hair"


class TestRealWorldScenarios:
    """Test real prompts from production that failed."""

    def test_scene2_match_rate_29_percent(self):
        """Scene 2 that had 29% match rate.

        Original problematic prompt from screenshot:
        - "short green hair" (0 Danbooru posts)
        - "thumbs up" (space instead of underscore)
        """
        input_prompt = "grin, sparkling eyes, thumbs up, standing, front view, flower field, outdoors, day, sunny, full body, soft light, short green hair, messy hair, freckles, laughing"
        result = normalize_and_fix_tags(input_prompt)

        # Should fix "thumbs up" → "thumbs_up"
        assert "thumbs_up" in result
        assert "thumbs up" not in result

        # Should fix "short green hair" → "short_hair, green_hair"
        assert "short_hair" in result
        assert "green_hair" in result
        assert "short_green_hair" not in result

        # Should preserve other tags
        assert "grin" in result
        assert "standing" in result
        assert "flower_field" in result  # Also normalized space

    def test_gemini_typical_output(self):
        """Typical Gemini output with multiple issues."""
        input_prompt = "happy, long blonde hair, looking at viewer, white dress, outdoors, day, full body"
        result = normalize_and_fix_tags(input_prompt)

        # All spaces normalized
        assert "looking_at_viewer" in result
        assert "full_body" in result

        # Compound adjectives split
        assert "long_hair" in result
        assert "blonde_hair" in result

        # Valid tags preserved
        assert "happy" in result
        assert "white_dress" in result
        assert "outdoors" in result


class TestDanbooruValidation:
    """Test Danbooru API validation (Phase 2 - smart caching)."""

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_fast_path_db_tags(self, mock_danbooru, mock_session):
        """Tags in DB should not call Danbooru API (fast path)."""
        # Mock DB with existing tags
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        mock_tag = MagicMock()
        mock_tag.name = "smile"
        mock_db.query.return_value.all.return_value = [
            type("Tag", (), {"name": "smile"}),
            type("Tag", (), {"name": "standing"}),
        ]

        result = validate_tags_with_danbooru(["smile", "standing"])

        # Should return tags without calling Danbooru
        assert result == ["smile", "standing"]
        assert mock_danbooru.call_count == 0  # No API calls

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_slow_path_valid_new_tag(self, mock_danbooru, mock_session):
        """New tags with >0 posts should be added to DB."""
        # Mock empty DB
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = []

        # Mock Danbooru response: valid tag
        mock_danbooru.return_value = {
            "post_count": 17480,
            "category": "general",
        }

        result = validate_tags_with_danbooru(["thumbs_up"])

        # Should accept and add to DB
        assert result == ["thumbs_up"]
        assert mock_danbooru.call_count == 1
        assert mock_db.add.called  # Added to DB
        assert mock_db.commit.called

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_slow_path_invalid_tag_0_posts(self, mock_danbooru, mock_session):
        """Tags with 0 posts should attempt compound splitting."""
        # Mock empty DB
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = []

        # Mock Danbooru response: invalid tag (0 posts)
        mock_danbooru.return_value = {
            "post_count": 0,
            "category": "general",
        }

        result = validate_tags_with_danbooru(["short_green_hair"])

        # Should split compound
        assert "short_hair" in result
        assert "green_hair" in result
        assert "short_green_hair" not in result

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_session_cache_avoids_duplicate_calls(self, mock_danbooru, mock_session):
        """Same tag twice should use session cache (1 API call)."""
        # Mock empty DB
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = []

        # Mock Danbooru response
        mock_danbooru.return_value = {
            "post_count": 17480,
            "category": "general",
        }

        # Call with duplicate tags
        result = validate_tags_with_danbooru(["thumbs_up", "thumbs_up"])

        # Should only call Danbooru once (session cache)
        assert result == ["thumbs_up", "thumbs_up"]
        assert mock_danbooru.call_count == 1  # Only 1 API call

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_mixed_db_and_new_tags(self, mock_danbooru, mock_session):
        """Mix of DB tags (fast) and new tags (slow) should be efficient."""
        # Mock DB with some tags
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = [
            type("Tag", (), {"name": "smile"}),
            type("Tag", (), {"name": "standing"}),
        ]

        # Mock Danbooru response for new tag
        mock_danbooru.return_value = {
            "post_count": 17480,
            "category": "general",
        }

        result = validate_tags_with_danbooru(["smile", "thumbs_up", "standing"])

        # Should return all tags
        assert "smile" in result
        assert "thumbs_up" in result
        assert "standing" in result

        # Should only call Danbooru for new tag
        assert mock_danbooru.call_count == 1

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_danbooru_api_error_handling(self, mock_danbooru, mock_session):
        """API errors should fail-open (keep tag)."""
        # Mock empty DB
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = []

        # Mock Danbooru API error
        mock_danbooru.side_effect = Exception("API timeout")

        result = validate_tags_with_danbooru(["unknown_tag"])

        # Should keep tag despite error (fail-open)
        assert result == ["unknown_tag"]

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_underscore_space_fallback_db(self, mock_danbooru, mock_session):
        """Tags should match both underscore and space formats in DB."""
        # Mock DB with SPACE-format tags (legacy)
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = [
            type("Tag", (), {"name": "looking at viewer"}),  # Space format
            type("Tag", (), {"name": "thumbs up"}),  # Space format
        ]

        # Query with UNDERSCORE format (normalized)
        result = validate_tags_with_danbooru(["looking_at_viewer", "thumbs_up"])

        # Should match via fallback
        assert result == ["looking_at_viewer", "thumbs_up"]
        assert mock_danbooru.call_count == 0  # No API calls (DB matched)

    @patch("database.SessionLocal")
    @patch("services.danbooru.get_tag_info_sync")
    def test_danbooru_api_space_fallback(self, mock_danbooru, mock_session):
        """Danbooru API should try space format if underscore fails."""
        # Mock empty DB
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.all.return_value = []

        # Mock Danbooru: underscore fails (0 posts), space succeeds
        def danbooru_response(tag):
            if tag == "looking_at_viewer":
                return {"post_count": 0, "category": "general"}  # Fail
            elif tag == "looking at viewer":
                return {"post_count": 2900000, "category": "general"}  # Success
            return {"post_count": 0, "category": "general"}

        mock_danbooru.side_effect = danbooru_response

        result = validate_tags_with_danbooru(["looking_at_viewer"])

        # Should succeed via space fallback
        assert result == ["looking_at_viewer"]
        assert mock_danbooru.call_count == 2  # Tried both formats
        # Check calls: first underscore, then space
        calls = [str(call) for call in mock_danbooru.call_args_list]
        assert "looking_at_viewer" in calls[0]
        assert "looking at viewer" in calls[1]
