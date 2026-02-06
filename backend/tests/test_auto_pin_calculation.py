"""Tests for calculate_auto_pin_flags function.

This function calculates _auto_pin_previous flags for scenes based on
environment tags. Scenes with overlapping environment tags should auto-pin.
"""

from unittest.mock import MagicMock


def create_mock_scene(scene_id: int, env_tags: list[str] | None = None):
    """Create a mock Scene object with context_tags."""
    scene = MagicMock()
    scene.id = scene_id
    scene.context_tags = {"environment": env_tags} if env_tags else None
    return scene


class TestCalculateAutoPinFlags:
    """Test calculate_auto_pin_flags function."""

    def test_single_scene_no_pin(self):
        """Single scene should not have auto-pin (no previous scene)."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [create_mock_scene(1, ["office", "indoors"])]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False

    def test_two_scenes_same_location_should_pin(self):
        """Second scene with same environment should auto-pin."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["office", "indoors"]),
            create_mock_scene(2, ["office", "indoors"]),
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False  # First scene
        assert result[2] is True  # Same location → auto-pin

    def test_two_scenes_different_location_no_pin(self):
        """Second scene with different environment should not auto-pin."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["office", "indoors"]),
            create_mock_scene(2, ["park", "outdoors"]),
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False
        assert result[2] is False  # Different location → no pin

    def test_partial_overlap_should_pin(self):
        """Scenes with at least one overlapping tag should auto-pin."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["office", "indoors"]),
            create_mock_scene(2, ["hallway", "indoors"]),  # "indoors" overlaps
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False
        assert result[2] is True  # Partial overlap → auto-pin

    def test_multiple_scenes_mixed(self):
        """Multiple scenes with location changes."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["cafe", "indoors"]),
            create_mock_scene(2, ["cafe", "indoors"]),  # Same
            create_mock_scene(3, ["park", "outdoors"]),  # Different
            create_mock_scene(4, ["park", "bench"]),  # "park" overlaps
            create_mock_scene(5, ["office", "indoors"]),  # Different
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False  # First scene
        assert result[2] is True  # Same as scene 1
        assert result[3] is False  # Location changed
        assert result[4] is True  # "park" overlaps with scene 3
        assert result[5] is False  # Location changed

    def test_empty_environment_tags(self):
        """Scene with empty environment tags should not pin."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["office"]),
            create_mock_scene(2, []),  # Empty
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False
        assert result[2] is False  # Empty tags → no pin

    def test_none_context_tags(self):
        """Scene with None context_tags should not pin."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["office"]),
            create_mock_scene(2, None),  # None
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False
        assert result[2] is False  # None tags → no pin

    def test_previous_none_current_has_tags(self):
        """Previous scene has no tags, current has tags."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, None),
            create_mock_scene(2, ["office"]),
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False
        assert result[2] is False  # Previous had no tags → no overlap possible

    def test_empty_scenes_list(self):
        """Empty scenes list should return empty dict."""
        from services.storyboard import calculate_auto_pin_flags

        result = calculate_auto_pin_flags([])
        assert result == {}

    def test_chain_of_same_location(self):
        """Chain of scenes in same location should all auto-pin."""
        from services.storyboard import calculate_auto_pin_flags

        scenes = [
            create_mock_scene(1, ["cafe"]),
            create_mock_scene(2, ["cafe"]),
            create_mock_scene(3, ["cafe"]),
            create_mock_scene(4, ["cafe"]),
        ]
        result = calculate_auto_pin_flags(scenes)

        assert result[1] is False  # First
        assert result[2] is True
        assert result[3] is True
        assert result[4] is True
