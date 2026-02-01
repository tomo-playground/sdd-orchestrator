"""Tests for DB cache modules: TagCategoryCache, TagAliasCache, TagRuleCache, TagFilterCache."""

import pytest

from services.keywords.db_cache import TagCategoryCache


# ────────────────────────────────────────────
# D-6: Gemini Category Mapping Tests
# ────────────────────────────────────────────

class TestGeminiCategoryMapping:
    """Test Gemini context_tags → V3 Layer mapping (D-6)."""

    def test_expression_group_maps_correctly(self):
        """Gemini 'expression' group → returns 'expression' category."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name="expression"
        )
        assert result == "expression"

    def test_gaze_group_maps_correctly(self):
        """Gemini 'gaze' group → returns 'gaze' category."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name="gaze"
        )
        assert result == "gaze"

    def test_pose_group_maps_correctly(self):
        """Gemini 'pose' group → returns 'pose' category."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name="pose"
        )
        assert result == "pose"

    def test_action_group_maps_correctly(self):
        """Gemini 'action' group → returns 'action' category."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name="action"
        )
        assert result == "action"

    def test_camera_group_maps_correctly(self):
        """Gemini 'camera' group → returns 'camera' category."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name="camera"
        )
        assert result == "camera"

    def test_environment_groups_map_correctly(self):
        """Gemini environment groups → return their group names."""
        assert TagCategoryCache._map_db_category("scene", "location_indoor") == "location_indoor"
        assert TagCategoryCache._map_db_category("scene", "location_outdoor") == "location_outdoor"
        assert TagCategoryCache._map_db_category("scene", "time_weather") == "time_weather"
        assert TagCategoryCache._map_db_category("scene", "lighting") == "lighting"

    def test_mood_group_maps_correctly(self):
        """Gemini 'mood' group → returns 'mood' category."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name="mood"
        )
        assert result == "mood"

    def test_non_granular_group_falls_back_to_category(self):
        """Unknown group_name → fallback to category mapping."""
        result = TagCategoryCache._map_db_category(
            category="character",
            group_name="unknown_group"
        )
        # Should use DB_TO_PROMPT_CATEGORY mapping
        assert result == "identity"  # 'character' → 'identity'

    def test_scene_category_without_group(self):
        """category='scene' with no group_name → returns 'scene'."""
        result = TagCategoryCache._map_db_category(
            category="scene",
            group_name=None
        )
        assert result == "scene"

    def test_all_gemini_categories_covered(self):
        """Verify all Gemini context_tags categories have mappings."""
        gemini_groups = [
            "expression", "gaze", "pose", "action", "camera",
            "location_indoor", "location_outdoor", "time_weather", "lighting", "mood"
        ]

        for group in gemini_groups:
            result = TagCategoryCache._map_db_category("scene", group)
            # All should map to their group name (granular_groups set)
            assert result == group, f"Gemini group '{group}' should map to itself"
