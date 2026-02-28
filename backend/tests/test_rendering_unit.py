"""Unit tests for backend/services/rendering.py.

Covers core rendering functions: post frame composition, scene text rendering,
layout metrics, font sizing, brightness analysis, and common content drawing.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image_bytes(width: int = 512, height: int = 768, color: tuple = (128, 128, 128)) -> bytes:
    """Create a simple test image and return as bytes."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_overlay_settings(
    channel_name: str = "TestChannel",
    caption: str = "test caption #tag",
    avatar_file: str | None = None,
    frame_style: str = "overlay_clean.png",
    likes_count: str = "1.2만",
    posted_time: str = "5분 전",
) -> SimpleNamespace:
    """Create a minimal settings object for overlay tests."""
    return SimpleNamespace(
        channel_name=channel_name,
        caption=caption,
        avatar_file=avatar_file,
        frame_style=frame_style,
        likes_count=likes_count,
        posted_time=posted_time,
    )


# ===========================================================================
# 1. calculate_scene_text_area_height
# ===========================================================================


class TestCalculateSceneTextAreaHeight:
    """Tests for calculate_scene_text_area_height()."""

    def test_empty_text_returns_minimum(self):
        from services.rendering import calculate_scene_text_area_height

        result = calculate_scene_text_area_height("", 1000)
        assert result == int(1000 * 0.12)

    def test_none_text_returns_minimum(self):
        from services.rendering import calculate_scene_text_area_height

        result = calculate_scene_text_area_height(None, 1000)
        assert result == int(1000 * 0.12)

    def test_short_text_returns_12_percent(self):
        from services.rendering import calculate_scene_text_area_height

        result = calculate_scene_text_area_height("short", 1000)
        assert result == 120

    def test_long_text_over_60_chars(self):
        from services.rendering import calculate_scene_text_area_height

        long_text = "a" * 61
        result = calculate_scene_text_area_height(long_text, 1000)
        assert result == int(1000 * 0.25)

    def test_multiline_over_2_lines(self):
        from services.rendering import calculate_scene_text_area_height

        # 3 lines triggers max height regardless of char count
        text = "first line of text\nsecond line of text\nthird line of text"
        result = calculate_scene_text_area_height(text, 1000)
        assert result == int(1000 * 0.25)

    def test_medium_text_interpolation(self):
        from services.rendering import calculate_scene_text_area_height

        # 40 chars = midpoint of 20-60 range
        text = "a" * 40
        result = calculate_scene_text_area_height(text, 1000)
        expected_ratio = 0.12 + (40 - 20) * (0.18 - 0.12) / 40
        expected = int(1000 * expected_ratio)
        assert result == expected

    def test_boundary_20_chars(self):
        from services.rendering import calculate_scene_text_area_height

        text = "a" * 20
        result = calculate_scene_text_area_height(text, 1000)
        expected = int(1000 * 0.12)
        assert result == expected

    def test_boundary_60_chars(self):
        from services.rendering import calculate_scene_text_area_height

        text = "a" * 60
        result = calculate_scene_text_area_height(text, 1000)
        expected = int(1000 * 0.18)
        assert result == expected

    def test_different_card_height(self):
        from services.rendering import calculate_scene_text_area_height

        result = calculate_scene_text_area_height("", 500)
        assert result == int(500 * 0.12)


# ===========================================================================
# 2. calculate_optimal_font_size
# ===========================================================================


class TestCalculateOptimalFontSize:
    """Tests for calculate_optimal_font_size()."""

    def test_short_text_returns_max(self):
        from services.rendering import calculate_optimal_font_size

        result = calculate_optimal_font_size("hi", base_font_size=40)
        assert result == 48

    def test_long_text_returns_min(self):
        from services.rendering import calculate_optimal_font_size

        result = calculate_optimal_font_size("a" * 61, base_font_size=40)
        assert result == 32

    def test_custom_min_max(self):
        from services.rendering import calculate_optimal_font_size

        result = calculate_optimal_font_size("hi", base_font_size=40, min_font_size=20, max_font_size=60)
        assert result == 60

    def test_custom_min_max_long(self):
        from services.rendering import calculate_optimal_font_size

        result = calculate_optimal_font_size("a" * 70, base_font_size=40, min_font_size=20, max_font_size=60)
        assert result == 20

    def test_midpoint_interpolation(self):
        from services.rendering import calculate_optimal_font_size

        text = "a" * 40  # midpoint of 20-60
        result = calculate_optimal_font_size(text, base_font_size=40)
        ratio = (40 - 20) / 40
        expected = int(48 - (48 - 32) * ratio)
        assert result == expected

    def test_empty_text_treated_as_short(self):
        from services.rendering import calculate_optimal_font_size

        result = calculate_optimal_font_size("", base_font_size=40)
        assert result == 48  # max for short text

    def test_whitespace_stripped(self):
        from services.rendering import calculate_optimal_font_size

        result = calculate_optimal_font_size("   abc   ", base_font_size=40)
        assert result == 48  # 5 chars after strip < 20


# ===========================================================================
# 3. calculate_post_layout_metrics
# ===========================================================================


class TestCalculatePostLayoutMetrics:
    """Tests for calculate_post_layout_metrics()."""

    def test_returns_all_required_keys(self):
        from services.rendering import calculate_post_layout_metrics

        metrics = calculate_post_layout_metrics(1080, 1920)
        expected_keys = {
            "card_width",
            "card_height",
            "card_padding",
            "card_x",
            "card_y",
            "header_height",
            "scene_text_area_height",
            "action_bar_height",
            "caption_height",
            "image_area",
            "image_x",
            "image_y",
            "scene_text_y",
        }
        assert expected_keys.issubset(set(metrics.keys()))

    def test_card_width_is_88_percent(self):
        from services.rendering import calculate_post_layout_metrics

        metrics = calculate_post_layout_metrics(1000, 1000)
        assert metrics["card_width"] == int(1000 * 0.88)

    def test_card_height_is_86_percent(self):
        from services.rendering import calculate_post_layout_metrics

        metrics = calculate_post_layout_metrics(1000, 1000)
        assert metrics["card_height"] == int(1000 * 0.86)

    def test_image_area_positive(self):
        from services.rendering import calculate_post_layout_metrics

        metrics = calculate_post_layout_metrics(1080, 1920)
        assert metrics["image_area"] > 0

    def test_scene_text_height_varies_with_text(self):
        from services.rendering import calculate_post_layout_metrics

        short_metrics = calculate_post_layout_metrics(1080, 1920, "hi")
        long_metrics = calculate_post_layout_metrics(1080, 1920, "a" * 70)
        assert long_metrics["scene_text_area_height"] > short_metrics["scene_text_area_height"]

    def test_backward_compat_no_text(self):
        from services.rendering import calculate_post_layout_metrics

        metrics = calculate_post_layout_metrics(1080, 1920)
        assert "scene_text_area_height" in metrics


# ===========================================================================
# 4. render_scene_text_image
# ===========================================================================


class TestRenderSceneTextImage:
    """Tests for render_scene_text_image()."""

    def test_empty_lines_returns_transparent(self):
        from services.rendering import render_scene_text_image

        result = render_scene_text_image(
            lines=[],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
        )
        assert result.mode == "RGBA"
        assert result.size == (1080, 1920)
        # All pixels should be fully transparent
        pixels = list(result.getdata())
        assert all(p[3] == 0 for p in pixels)

    def test_full_layout_returns_correct_size(self):
        from services.rendering import render_scene_text_image

        result = render_scene_text_image(
            lines=["Hello world"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
        )
        assert result.size == (1080, 1920)
        assert result.mode == "RGBA"

    def test_full_layout_has_visible_pixels(self):
        from services.rendering import render_scene_text_image

        result = render_scene_text_image(
            lines=["Test text"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
        )
        pixels = list(result.getdata())
        non_transparent = [p for p in pixels if p[3] > 0]
        assert len(non_transparent) > 0, "Text should produce visible pixels"

    def test_post_layout_renders(self):
        from services.rendering import calculate_post_layout_metrics, render_scene_text_image

        metrics = calculate_post_layout_metrics(1080, 1920, "test text")
        result = render_scene_text_image(
            lines=["test text"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=True,
            post_layout_metrics=metrics,
        )
        assert result.size == (1080, 1920)
        assert result.mode == "RGBA"

    def test_font_size_override(self):
        from services.rendering import render_scene_text_image

        result = render_scene_text_image(
            lines=["override size"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
            font_size_override=64,
        )
        assert result.size == (1080, 1920)

    def test_scene_text_y_ratio(self):
        from services.rendering import render_scene_text_image

        result = render_scene_text_image(
            lines=["positioned text"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
            scene_text_y_ratio=0.5,
        )
        assert result.size == (1080, 1920)

    def test_adaptive_text_color_bright_background(self):
        """Bright background should produce dark text pixels."""
        from services.rendering import render_scene_text_image

        bright_bg = Image.new("RGB", (1080, 1920), (255, 255, 255))
        result = render_scene_text_image(
            lines=["adaptive color"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
            background_image=bright_bg,
        )
        assert result.size == (1080, 1920)

    def test_adaptive_text_color_dark_background(self):
        """Dark background should produce light text pixels."""
        from services.rendering import render_scene_text_image

        dark_bg = Image.new("RGB", (1080, 1920), (0, 0, 0))
        result = render_scene_text_image(
            lines=["adaptive color"],
            width=1080,
            height=1920,
            font_path="Arial",
            use_post_layout=False,
            post_layout_metrics=None,
            background_image=dark_bg,
        )
        assert result.size == (1080, 1920)


# ===========================================================================
# 5. analyze_text_region_brightness
# ===========================================================================


class TestAnalyzeTextRegionBrightness:
    """Tests for analyze_text_region_brightness()."""

    def test_white_image_high_brightness(self):
        from services.image import analyze_text_region_brightness

        img = Image.new("RGB", (1080, 1920), (255, 255, 255))
        brightness = analyze_text_region_brightness(img, 0.7)
        assert brightness > 200

    def test_black_image_low_brightness(self):
        from services.image import analyze_text_region_brightness

        img = Image.new("RGB", (1080, 1920), (0, 0, 0))
        brightness = analyze_text_region_brightness(img, 0.7)
        assert brightness < 10

    def test_mid_gray_image(self):
        from services.image import analyze_text_region_brightness

        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        brightness = analyze_text_region_brightness(img, 0.7)
        assert 120 < brightness < 140

    def test_different_y_ratios(self):
        from services.image import analyze_text_region_brightness

        img = Image.new("RGB", (1080, 1920), (100, 100, 100))
        b1 = analyze_text_region_brightness(img, 0.1)
        b2 = analyze_text_region_brightness(img, 0.9)
        # Uniform image should give same result
        assert abs(b1 - b2) < 5


# ===========================================================================
# 6. calculate_optimal_scene_text_y
# ===========================================================================


class TestCalculateOptimalSceneTextY:
    """Tests for calculate_optimal_scene_text_y()."""

    def test_returns_float(self):
        from services.image import calculate_optimal_scene_text_y

        img = Image.new("RGB", (512, 768), (128, 128, 128))
        result = calculate_optimal_scene_text_y(img)
        assert isinstance(result, float)

    def test_result_in_valid_range(self):
        from services.image import calculate_optimal_scene_text_y

        img = Image.new("RGB", (512, 768), (128, 128, 128))
        result = calculate_optimal_scene_text_y(img)
        assert 0.0 <= result <= 1.0

    def test_platform_youtube_shorts(self):
        from services.image import calculate_optimal_scene_text_y

        img = Image.new("RGB", (512, 768), (128, 128, 128))
        result = calculate_optimal_scene_text_y(img, platform="youtube_shorts")
        assert result <= 0.85  # Should respect 15% safe zone

    def test_platform_tiktok(self):
        from services.image import calculate_optimal_scene_text_y

        img = Image.new("RGB", (512, 768), (128, 128, 128))
        result = calculate_optimal_scene_text_y(img, platform="tiktok")
        assert result <= 0.80  # Should respect 20% safe zone


# ===========================================================================
# 7. compose_post_frame
# ===========================================================================


class TestComposePostFrame:
    """Tests for compose_post_frame()."""

    @patch("services.image.detect_face", return_value=None)
    def test_returns_rgb_image(self, mock_face):
        from services.rendering import compose_post_frame

        image_bytes = _make_image_bytes()
        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1920,
            channel_name="TestCh",
            caption="test caption",
            subtitle_text="test subtitle",
            font_path="Arial",
        )
        assert result.mode == "RGB"
        assert result.size == (1080, 1920)

    @patch("services.image.detect_face", return_value=None)
    def test_without_subtitle(self, mock_face):
        from services.rendering import compose_post_frame

        image_bytes = _make_image_bytes()
        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1920,
            channel_name="TestCh",
            caption="test caption #tag",
            subtitle_text="",
            font_path="Arial",
        )
        assert result.mode == "RGB"
        assert result.size == (1080, 1920)

    @patch("services.image.detect_face", return_value=None)
    def test_with_views_and_time_override(self, mock_face):
        from services.rendering import compose_post_frame

        image_bytes = _make_image_bytes()
        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1920,
            channel_name="TestCh",
            caption="test",
            subtitle_text="text",
            font_path="Arial",
            views_override="10만",
            time_override="1시간 전",
        )
        assert result.size == (1080, 1920)

    @patch("services.image.calculate_face_centered_crop", return_value=(50, 50, 400, 400))
    @patch("services.image.detect_face", return_value=(100, 100, 200, 200))
    def test_with_face_detection(self, mock_face, mock_crop):
        from services.rendering import compose_post_frame

        image_bytes = _make_image_bytes()
        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1920,
            channel_name="TestCh",
            caption="test",
            subtitle_text="subtitle",
            font_path="Arial",
        )
        assert result.size == (1080, 1920)
        mock_face.assert_called_once()
        mock_crop.assert_called_once()


# ===========================================================================
# 8. _draw_common_content
# ===========================================================================


class TestDrawCommonContent:
    """Tests for _draw_common_content()."""

    @patch("services.rendering.load_avatar_image", return_value=None)
    def test_draws_without_avatar(self, mock_avatar):
        from services.rendering import _draw_common_content

        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        settings = _make_overlay_settings()

        _draw_common_content(
            draw=draw,
            canvas=canvas,
            width=1080,
            height=1920,
            settings=settings,
            safe_margin=64,
            header_top=76,
            header_height=96,
            footer_top=1536,
            footer_height=192,
        )
        # Should not raise, canvas should have content
        pixels = list(canvas.getdata())
        non_transparent = [p for p in pixels if p[3] > 0]
        assert len(non_transparent) > 0

    @patch("services.rendering.load_avatar_image")
    def test_draws_with_avatar(self, mock_avatar):
        avatar_img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        mock_avatar.return_value = avatar_img

        from services.rendering import _draw_common_content

        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        settings = _make_overlay_settings(avatar_file="avatar.png")

        _draw_common_content(
            draw=draw,
            canvas=canvas,
            width=1080,
            height=1920,
            settings=settings,
            safe_margin=64,
            header_top=76,
            header_height=96,
            footer_top=1536,
            footer_height=192,
        )
        pixels = list(canvas.getdata())
        non_transparent = [p for p in pixels if p[3] > 0]
        assert len(non_transparent) > 0

    @patch("services.rendering.load_avatar_image", return_value=None)
    def test_stroke_mode(self, mock_avatar):
        from services.rendering import _draw_common_content

        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        settings = _make_overlay_settings()

        _draw_common_content(
            draw=draw,
            canvas=canvas,
            width=1080,
            height=1920,
            settings=settings,
            safe_margin=64,
            header_top=76,
            header_height=96,
            footer_top=1536,
            footer_height=192,
            use_stroke=True,
        )
        # Should not raise
        assert canvas.size == (1080, 1920)

    @patch("services.rendering.load_avatar_image", return_value=None)
    def test_show_meta(self, mock_avatar):
        from services.rendering import _draw_common_content

        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        settings = _make_overlay_settings()

        _draw_common_content(
            draw=draw,
            canvas=canvas,
            width=1080,
            height=1920,
            settings=settings,
            safe_margin=64,
            header_top=76,
            header_height=96,
            footer_top=1536,
            footer_height=192,
            show_meta=True,
        )
        assert canvas.size == (1080, 1920)

    @patch("services.rendering.load_avatar_image", return_value=None)
    def test_with_offset(self, mock_avatar):
        from services.rendering import _draw_common_content

        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        settings = _make_overlay_settings()

        _draw_common_content(
            draw=draw,
            canvas=canvas,
            width=800,
            height=1400,
            settings=settings,
            safe_margin=48,
            header_top=56,
            header_height=70,
            footer_top=1120,
            footer_height=140,
            offset_x=50,
            offset_y=100,
        )
        assert canvas.size == (1080, 1920)


# ===========================================================================
# 9. Helper functions
# ===========================================================================


class TestHelperFunctions:
    """Tests for small helper functions in rendering.py."""

    def test_format_views_man(self):
        from services.rendering import _format_views

        assert _format_views(10000) == "1만"
        assert _format_views(50000) == "5만"

    def test_format_views_cheon(self):
        from services.rendering import _format_views

        assert _format_views(1000) == "1천"
        assert _format_views(9999) == "9천"

    def test_format_views_small(self):
        from services.rendering import _format_views

        assert _format_views(500) == "500"
        assert _format_views(0) == "0"

    def test_clean_caption_title_removes_hashtags(self):
        from services.rendering import _clean_caption_title

        result = _clean_caption_title("hello #world #test")
        assert "#" not in result
        assert "hello" in result

    def test_clean_caption_title_truncates(self):
        from services.rendering import _clean_caption_title

        long_text = "a" * 100
        result = _clean_caption_title(long_text)
        assert len(result) <= 50

    def test_seeded_int_deterministic(self):
        from services.rendering import _seeded_int

        val1 = _seeded_int("test_key")
        val2 = _seeded_int("test_key")
        assert val1 == val2

    def test_seeded_int_different_keys(self):
        from services.rendering import _seeded_int

        val1 = _seeded_int("key_a")
        val2 = _seeded_int("key_b")
        # Different keys should (almost certainly) produce different values
        assert val1 != val2

    def test_build_post_meta_returns_dict(self):
        from services.rendering import _build_post_meta

        result = _build_post_meta("channel", "caption text", "title text")
        assert "display_name" in result
        assert "timestamp" in result
        assert "views" in result
        assert "avatar_color" in result

    def test_build_post_meta_short_name_gets_suffix(self):
        from services.rendering import _build_post_meta

        result = _build_post_meta("AB", "cap", "ttl")
        assert len(result["display_name"]) >= 4

    def test_build_post_meta_overrides(self):
        from services.rendering import _build_post_meta

        result = _build_post_meta("ch", "cap", "ttl", views_override="99만", time_override="방금")
        assert result["views"] == "99만"
        assert result["timestamp"] == "방금"

    def test_is_emoji_char(self):
        from services.rendering import _is_emoji_char

        assert _is_emoji_char("\U0001f600")  # grinning face
        assert not _is_emoji_char("A")
        assert not _is_emoji_char("가")
