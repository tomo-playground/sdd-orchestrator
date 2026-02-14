"""Tests for layout improvements (Post Type dynamic height, Full Type safe zones)."""

import io

import pytest
from PIL import Image

from services.image import PLATFORM_SAFE_ZONES, calculate_optimal_scene_text_y
from services.rendering import calculate_post_layout_metrics, calculate_scene_text_area_height


class TestSceneTextAreaHeight:
    """Tests for dynamic scene text area height calculation."""

    def test_empty_text_returns_minimum_height(self):
        """Empty text should return minimum height (12%)."""
        result = calculate_scene_text_area_height("", 1000)
        assert result == 120  # 1000 * 0.12

    def test_short_text_returns_minimum_height(self):
        """Short text (< 20 chars) should return 12% height."""
        result = calculate_scene_text_area_height("짧은 텍스트", 1000)
        assert result == 120  # 1000 * 0.12

    def test_long_text_returns_maximum_height(self):
        """Long text (> 60 chars) should return 25% height."""
        long_text = "이것은 매우 긴 텍스트입니다. " * 5  # ~75 chars
        result = calculate_scene_text_area_height(long_text, 1000)
        assert result == 250  # 1000 * 0.25

    def test_multi_line_text_returns_maximum_height(self):
        """Multi-line text (> 2 lines) should return 25% height."""
        multi_line = "첫 번째 줄\n두 번째 줄\n세 번째 줄"
        result = calculate_scene_text_area_height(multi_line, 1000)
        assert result == 250  # 1000 * 0.25

    def test_medium_text_interpolates_height(self):
        """Medium length text (20-60 chars) should interpolate between 12-18%."""
        medium_text = "중간 길이의 텍스트입니다. 약 40자 정도."  # Actually ~21 chars
        char_count = len(medium_text.strip())
        result = calculate_scene_text_area_height(medium_text, 1000)
        # Should interpolate based on actual char count
        assert 120 <= result <= 180
        # More precise check based on actual char count
        if 20 <= char_count <= 60:
            expected = int(1000 * (0.12 + (char_count - 20) * (0.18 - 0.12) / 40))
            assert result == expected
        else:
            # If char count is outside range, just check bounds
            assert result in [120, 250]  # Min or max

    def test_whitespace_stripped(self):
        """Whitespace should be stripped before counting."""
        text_with_spaces = "   텍스트   "
        result = calculate_scene_text_area_height(text_with_spaces, 1000)
        assert result == 120  # Short text after stripping


class TestPostLayoutMetrics:
    """Tests for post layout metrics with dynamic scene text height."""

    def test_metrics_with_empty_text(self):
        """Metrics should work with empty text (minimum height)."""
        metrics = calculate_post_layout_metrics(1080, 1080, "")
        assert "scene_text_area_height" in metrics
        # Card height = 1080 * 0.86 = 928.8 → 928
        # Minimum height = 928 * 0.12 = 111.36 → 111
        assert metrics["scene_text_area_height"] == 111

    def test_metrics_with_long_text(self):
        """Metrics should adjust for long text (maximum height)."""
        long_text = "이것은 매우 긴 텍스트입니다. " * 5
        metrics = calculate_post_layout_metrics(1080, 1080, long_text)
        # Card height = 928, Maximum height = 928 * 0.25 = 232
        assert metrics["scene_text_area_height"] == 232

    def test_metrics_backward_compatible(self):
        """Metrics should work without subtitle_text (default empty)."""
        metrics = calculate_post_layout_metrics(1080, 1080)
        assert "scene_text_area_height" in metrics
        assert metrics["scene_text_area_height"] == 111  # Minimum


class TestPlatformSafeZones:
    """Tests for platform-specific safe zones."""

    @pytest.fixture
    def mock_image(self):
        """Create a simple test image."""
        img = Image.new("RGB", (512, 768), (128, 128, 128))
        return img

    def test_safe_zones_defined(self):
        """Platform safe zones should be defined."""
        assert "youtube_shorts" in PLATFORM_SAFE_ZONES
        assert "tiktok" in PLATFORM_SAFE_ZONES
        assert "instagram_reels" in PLATFORM_SAFE_ZONES
        assert "default" in PLATFORM_SAFE_ZONES

    def test_youtube_shorts_safe_zone(self, mock_image):
        """YouTube Shorts should have 15% bottom safe zone."""
        # Low complexity → would normally return 0.72
        # But safe zone limits to 0.85 (1.0 - 0.15)
        y_pos = calculate_optimal_scene_text_y(
            mock_image, layout_style="full", platform="youtube_shorts"
        )
        assert y_pos <= 0.85

    def test_tiktok_safe_zone(self, mock_image):
        """TikTok should have 20% bottom safe zone."""
        # Safe zone limits to 0.80 (1.0 - 0.20)
        y_pos = calculate_optimal_scene_text_y(mock_image, layout_style="full", platform="tiktok")
        assert y_pos <= 0.80

    def test_instagram_reels_safe_zone(self, mock_image):
        """Instagram Reels should have 18% bottom safe zone."""
        # Safe zone limits to 0.82 (1.0 - 0.18)
        y_pos = calculate_optimal_scene_text_y(mock_image, layout_style="full", platform="instagram_reels")
        assert y_pos <= 0.82

    def test_default_platform_safe_zone(self, mock_image):
        """Default platform should have 15% bottom safe zone."""
        y_pos = calculate_optimal_scene_text_y(mock_image, layout_style="full", platform="default")
        assert y_pos <= 0.85

    def test_unknown_platform_uses_default(self, mock_image):
        """Unknown platform should use default safe zone."""
        y_pos = calculate_optimal_scene_text_y(mock_image, layout_style="full", platform="unknown_platform")
        assert y_pos <= 0.85

    def test_post_layout_ignores_safe_zone(self, mock_image):
        """Post layout should not apply safe zone (different UI structure)."""
        # Post layout has its own positioning logic
        y_pos = calculate_optimal_scene_text_y(mock_image, layout_style="post", platform="youtube_shorts")
        # Post layout returns different values (0.78-0.85 range)
        assert 0.78 <= y_pos <= 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
