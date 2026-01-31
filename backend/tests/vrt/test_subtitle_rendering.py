"""
VRT tests for subtitle rendering.

Tests the render_subtitle_image function to ensure visual consistency.
"""

from pathlib import Path

import pytest

# Import the function under test
from services.rendering import render_subtitle_image
from tests.vrt.compare import VRTComparison


class TestSubtitleRenderingFull:
    """Tests for Full layout (9:16) subtitle rendering."""

    def test_full_layout_single_line(self, vrt: VRTComparison, sample_font_path: Path):
        """Test single line subtitle in Full layout."""
        result = render_subtitle_image(
            lines=["안녕하세요, 테스트입니다."],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_single_line.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_full_layout_multi_line(self, vrt: VRTComparison, sample_font_path: Path):
        """Test multi-line subtitle in Full layout."""
        result = render_subtitle_image(
            lines=["첫 번째 줄입니다.", "두 번째 줄입니다."],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_multi_line.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_full_layout_empty(self, vrt: VRTComparison, sample_font_path: Path):
        """Test empty subtitle returns transparent canvas."""
        result = render_subtitle_image(
            lines=[],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_empty.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_full_layout_long_text(self, vrt: VRTComparison, sample_font_path: Path):
        """Test long text subtitle in Full layout."""
        result = render_subtitle_image(
            lines=["이것은 매우 긴 텍스트로 화면에 어떻게 표시되는지 테스트합니다."],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_long_text.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"


class TestSubtitleRenderingPost:
    """Tests for Post layout (1:1) subtitle rendering."""

    @pytest.fixture
    def post_metrics(self) -> dict[str, int]:
        """Standard post layout metrics for 1080x1080."""
        return {
            "card_x": 54,  # 5% margin
            "card_width": 972,  # 90% of width
            "card_padding": 40,
            "scene_text_y": 800,
            "scene_text_area_height": 200,
        }

    def test_post_layout_single_line(
        self, vrt: VRTComparison, sample_font_path: Path, post_metrics: dict[str, int]
    ):
        """Test single line subtitle in Post layout."""
        result = render_subtitle_image(
            lines=["Post 레이아웃 테스트"],
            width=1080,
            height=1080,
            font_path=str(sample_font_path),
            use_post_layout=True,
            post_layout_metrics=post_metrics,
        )

        comparison = vrt.compare("subtitle/post_single_line.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_layout_multi_line(
        self, vrt: VRTComparison, sample_font_path: Path, post_metrics: dict[str, int]
    ):
        """Test multi-line subtitle in Post layout."""
        result = render_subtitle_image(
            lines=["첫 번째 줄", "두 번째 줄", "세 번째 줄"],
            width=1080,
            height=1080,
            font_path=str(sample_font_path),
            use_post_layout=True,
            post_layout_metrics=post_metrics,
        )

        comparison = vrt.compare("subtitle/post_multi_line.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"


class TestSubtitleRenderingEdgeCases:
    """Edge case tests for subtitle rendering."""

    def test_emoji_in_subtitle(self, vrt: VRTComparison, sample_font_path: Path):
        """Test subtitle with emoji characters."""
        result = render_subtitle_image(
            lines=["안녕하세요! 😊 반갑습니다!"],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_with_emoji.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_english_subtitle(self, vrt: VRTComparison, sample_font_path: Path):
        """Test English text subtitle."""
        result = render_subtitle_image(
            lines=["Hello, World!", "This is a test."],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_english.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_mixed_language_subtitle(self, vrt: VRTComparison, sample_font_path: Path):
        """Test mixed Korean and English subtitle."""
        result = render_subtitle_image(
            lines=["Hello 안녕 World 세상!"],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("subtitle/full_mixed_lang.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"
