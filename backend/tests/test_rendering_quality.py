"""Rendering quality function integration tests.

SP-063: Verify that rendering quality functions (face detection,
adaptive text color, platform safe zone) are properly called
in the rendering pipeline.
"""

from unittest.mock import patch

import pytest
from PIL import Image

from services.image import PLATFORM_SAFE_ZONES, calculate_optimal_scene_text_y


def _make_image_bytes(width=512, height=768, color=(128, 128, 128)):
    import io

    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===========================================================================
# DoD-1: Face Detection regression
# ===========================================================================


class TestFaceDetectionIntegration:
    """Verify detect_face -> calculate_face_centered_crop chain in compose_post_frame."""

    @patch("services.image.calculate_face_centered_crop", return_value=(50, 50, 400, 400))
    @patch("services.image.detect_face", return_value=(100, 100, 200, 200))
    def test_face_detected_uses_smart_crop(self, mock_face, mock_crop):
        from services.rendering import compose_post_frame

        result = compose_post_frame(
            image_bytes=_make_image_bytes(),
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

    @patch("services.image.detect_face", return_value=None)
    def test_no_face_falls_back_to_imageops_fit(self, mock_face):
        from services.rendering import compose_post_frame

        result = compose_post_frame(
            image_bytes=_make_image_bytes(),
            width=1080,
            height=1920,
            channel_name="TestCh",
            caption="test",
            subtitle_text="subtitle",
            font_path="Arial",
        )
        assert result.size == (1080, 1920)
        mock_face.assert_called_once()


# ===========================================================================
# DoD-2: Adaptive text color regression
# ===========================================================================


class TestAdaptiveTextColorIntegration:
    """Verify analyze_text_region_brightness is called with background_image."""

    def test_bright_background_triggers_analysis(self):
        from services.rendering import render_scene_text_image

        bright_bg = Image.new("RGB", (512, 768), (240, 240, 240))
        with patch("services.image.analyze_text_region_brightness", return_value=200) as mock_brightness:
            result = render_scene_text_image(
                lines=["Test text"],
                width=512,
                height=768,
                font_path="Arial",
                use_post_layout=False,
                post_layout_metrics=None,
                background_image=bright_bg,
            )
            mock_brightness.assert_called_once()
            assert result.mode == "RGBA"

    def test_dark_background_triggers_analysis(self):
        from services.rendering import render_scene_text_image

        dark_bg = Image.new("RGB", (512, 768), (20, 20, 20))
        with patch("services.image.analyze_text_region_brightness", return_value=50) as mock_brightness:
            result = render_scene_text_image(
                lines=["Test text"],
                width=512,
                height=768,
                font_path="Arial",
                use_post_layout=False,
                post_layout_metrics=None,
                background_image=dark_bg,
            )
            mock_brightness.assert_called_once()
            assert result.mode == "RGBA"

    def test_no_background_skips_analysis(self):
        from services.rendering import render_scene_text_image

        with patch("services.image.analyze_text_region_brightness") as mock_brightness:
            result = render_scene_text_image(
                lines=["Test text"],
                width=512,
                height=768,
                font_path="Arial",
                use_post_layout=False,
                post_layout_metrics=None,
                background_image=None,
            )
            mock_brightness.assert_not_called()
            assert result.mode == "RGBA"


# ===========================================================================
# DoD-4: Platform Safe Zone
# ===========================================================================


class TestPlatformSafeZone:
    """Verify platform parameter is passed and affects Y position."""

    def test_youtube_shorts_safe_zone(self):
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y = calculate_optimal_scene_text_y(img, layout_style="full", platform="youtube_shorts")
        max_y = 1.0 - PLATFORM_SAFE_ZONES["youtube_shorts"]  # 0.85
        assert y <= max_y, f"Y={y} exceeds youtube_shorts safe zone max={max_y}"

    def test_tiktok_safe_zone(self):
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y = calculate_optimal_scene_text_y(img, layout_style="full", platform="tiktok")
        max_y = 1.0 - PLATFORM_SAFE_ZONES["tiktok"]  # 0.75
        assert y <= max_y, f"Y={y} exceeds tiktok safe zone max={max_y}"

    def test_instagram_reels_safe_zone(self):
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y = calculate_optimal_scene_text_y(img, layout_style="full", platform="instagram_reels")
        max_y = 1.0 - PLATFORM_SAFE_ZONES["instagram_reels"]  # 0.82
        assert y <= max_y, f"Y={y} exceeds instagram_reels safe zone max={max_y}"

    def test_default_platform_fallback(self):
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y = calculate_optimal_scene_text_y(img, layout_style="full", platform="default")
        max_y = 1.0 - PLATFORM_SAFE_ZONES["default"]  # 0.85
        assert y <= max_y, f"Y={y} exceeds default safe zone max={max_y}"

    def test_unknown_platform_uses_fallback(self):
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y = calculate_optimal_scene_text_y(img, layout_style="full", platform="unknown_platform")
        assert y <= 0.85, f"Unknown platform Y={y} should use fallback 0.15 safe zone"

    def test_tiktok_y_lower_than_youtube(self):
        """TikTok has larger safe zone (25%) than YouTube (15%), so max Y should be lower."""
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y_yt = calculate_optimal_scene_text_y(img, layout_style="full", platform="youtube_shorts")
        y_tt = calculate_optimal_scene_text_y(img, layout_style="full", platform="tiktok")
        assert y_tt <= y_yt, f"TikTok Y={y_tt} should be <= YouTube Y={y_yt}"

    def test_post_layout_ignores_platform(self):
        """Post layout should not be affected by platform parameter."""
        img = Image.new("RGB", (1080, 1920), (128, 128, 128))
        y_yt = calculate_optimal_scene_text_y(img, layout_style="post", platform="youtube_shorts")
        y_tt = calculate_optimal_scene_text_y(img, layout_style="post", platform="tiktok")
        assert y_yt == y_tt, "Post layout should ignore platform"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
