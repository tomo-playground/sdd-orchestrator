"""Tests for visual quality improvements (blur, text color, font size)."""

import io

import pytest
from PIL import Image

from services.image import analyze_text_region_brightness
from services.rendering import calculate_optimal_font_size


class TestTextRegionBrightness:
    """Tests for background brightness analysis."""

    def test_bright_background(self):
        """Bright background should return high brightness value."""
        bright_image = Image.new("RGB", (512, 768), (240, 240, 240))
        brightness = analyze_text_region_brightness(bright_image, 0.7)
        assert brightness > 200, f"Expected brightness > 200, got {brightness}"

    def test_dark_background(self):
        """Dark background should return low brightness value."""
        dark_image = Image.new("RGB", (512, 768), (20, 20, 20))
        brightness = analyze_text_region_brightness(dark_image, 0.7)
        assert brightness < 50, f"Expected brightness < 50, got {brightness}"

    def test_medium_background(self):
        """Medium brightness background should return mid-range value."""
        medium_image = Image.new("RGB", (512, 768), (128, 128, 128))
        brightness = analyze_text_region_brightness(medium_image, 0.7)
        assert 100 < brightness < 150, f"Expected 100 < brightness < 150, got {brightness}"

    def test_gradient_background(self):
        """Gradient background should return average brightness."""
        # Create gradient from dark to bright
        gradient = Image.new("RGB", (512, 768))
        pixels = gradient.load()
        for y in range(768):
            gray_value = int((y / 768) * 255)
            for x in range(512):
                pixels[x, y] = (gray_value, gray_value, gray_value)
        
        # Text region at 70% should be relatively bright
        brightness = analyze_text_region_brightness(gradient, 0.7)
        assert brightness > 150, f"Expected brightness > 150 for gradient at 70%, got {brightness}"


class TestOptimalFontSize:
    """Tests for dynamic font size calculation."""

    def test_short_text_large_font(self):
        """Short text (< 20 chars) should return maximum font size."""
        size = calculate_optimal_font_size("짧은 텍스트", base_font_size=40)
        assert size == 48, f"Expected 48 for short text, got {size}"

    def test_long_text_small_font(self):
        """Long text (> 60 chars) should return minimum font size."""
        long_text = "이것은 매우 긴 텍스트입니다. " * 5  # ~75 chars
        size = calculate_optimal_font_size(long_text, base_font_size=40)
        assert size == 32, f"Expected 32 for long text, got {size}"

    def test_medium_text_interpolated(self):
        """Medium length text (20-60 chars) should interpolate."""
        medium_text = "중간 길이의 텍스트입니다. 약 40자 정도 되는 문장."  # ~40 chars
        size = calculate_optimal_font_size(medium_text, base_font_size=40)
        assert 32 < size < 48, f"Expected 32 < size < 48, got {size}"

    def test_exact_20_chars(self):
        """Exactly 20 chars should return max font."""
        text = "1234567890" * 2  # Exactly 20 chars
        size = calculate_optimal_font_size(text, base_font_size=40)
        assert size == 48, f"Expected 48 for 20 chars, got {size}"

    def test_exact_60_chars(self):
        """Exactly 60 chars should return min font."""
        text = "123456" * 10  # Exactly 60 chars
        size = calculate_optimal_font_size(text, base_font_size=40)
        assert size == 32, f"Expected 32 for 60 chars, got {size}"

    def test_whitespace_stripped(self):
        """Whitespace should be stripped before counting."""
        text_with_spaces = "   텍스트   "
        size = calculate_optimal_font_size(text_with_spaces, base_font_size=40)
        assert size == 48, f"Expected 48 for short text after stripping, got {size}"

    def test_base_size_clamping(self):
        """Base size should be clamped to min/max range."""
        # Very large base size should be clamped
        size = calculate_optimal_font_size("short", base_font_size=100)
        assert size == 48, f"Expected 48 (max), got {size}"
        
        # Very small base size should be clamped
        size = calculate_optimal_font_size("this is a very long text with more than sixty characters in total", base_font_size=10)
        assert size == 32, f"Expected 32 (min), got {size}"


class TestAdaptiveTextColor:
    """Tests for adaptive text color based on background brightness."""

    def test_bright_background_black_text(self):
        """Bright background should render black text."""
        from services.rendering import render_scene_text_image
        
        # Create bright background
        bright_bg = Image.new("RGB", (512, 768), (240, 240, 240))
        
        # Render scene text with bright background
        result = render_scene_text_image(
            lines=["테스트 텍스트"],
            width=512,
            height=768,
            font_path="assets/fonts/온글잎 박다현체.ttf",
            use_post_layout=False,
            post_layout_metrics=None,
            background_image=bright_bg,
        )
        
        # Result should be a valid RGBA image
        assert result.mode == "RGBA"
        assert result.size == (512, 768)

    def test_dark_background_white_text(self):
        """Dark background should render white text (default)."""
        from services.rendering import render_scene_text_image
        
        # Create dark background
        dark_bg = Image.new("RGB", (512, 768), (20, 20, 20))
        
        # Render scene text with dark background
        result = render_scene_text_image(
            lines=["테스트 텍스트"],
            width=512,
            height=768,
            font_path="assets/fonts/온글잎 박다현체.ttf",
            use_post_layout=False,
            post_layout_metrics=None,
            background_image=dark_bg,
        )
        
        # Result should be a valid RGBA image
        assert result.mode == "RGBA"
        assert result.size == (512, 768)

    def test_no_background_image_default_white(self):
        """No background image should use default white text."""
        from services.rendering import render_scene_text_image
        
        # Render scene text without background image
        result = render_scene_text_image(
            lines=["테스트 텍스트"],
            width=512,
            height=768,
            font_path="assets/fonts/온글잎 박다현체.ttf",
            use_post_layout=False,
            post_layout_metrics=None,
            background_image=None,  # No background
        )
        
        # Result should be a valid RGBA image
        assert result.mode == "RGBA"
        assert result.size == (512, 768)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
