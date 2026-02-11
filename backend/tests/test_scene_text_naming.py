"""Test for scene text naming refactoring (TDD).

Ensures new naming convention is used throughout:
- subtitles → scene_text
- include_subtitles → include_scene_text
"""

import pytest

from schemas import VideoRequest


class TestSceneTextNaming:
    """Test scene text naming convention."""

    def test_video_request_has_include_scene_text_field(self):
        """VideoRequest should have include_scene_text field (not include_subtitles)."""
        request = VideoRequest(
            scenes=[],
            layout_style="full",
            width=1080,
            height=1920,
            include_scene_text=True,  # NEW NAMING
            narrator_voice="ko-KR-SunHiNeural",
        )

        assert hasattr(request, "include_scene_text")
        assert request.include_scene_text is True

    def test_post_layout_metrics_naming(self):
        """Post layout metrics should use scene_text naming."""
        from services.rendering import calculate_post_layout_metrics

        metrics = calculate_post_layout_metrics(1080, 1080)

        # NEW NAMING
        assert "scene_text_y" in metrics
        assert "scene_text_area_height" in metrics

        # Should NOT have old naming
        assert "subtitle_y" not in metrics
        assert "subtitle_area_height" not in metrics

    def test_full_layout_constants_naming(self):
        """Full layout constants should use scene_text naming."""
        from constants.layout import FullLayout

        # NEW NAMING
        assert hasattr(FullLayout, "SCENE_TEXT_FONT_RATIO")
        assert hasattr(FullLayout, "SCENE_TEXT_MIN_FONT_RATIO")
        assert hasattr(FullLayout, "SCENE_TEXT_Y_SINGLE_LINE_RATIO")

        # OLD NAMING (deprecated but still available for backward compatibility)
        assert hasattr(FullLayout, "SUBTITLE_FONT_RATIO")
        # Verify aliases point to same values
        assert FullLayout.SUBTITLE_FONT_RATIO == FullLayout.SCENE_TEXT_FONT_RATIO

    def test_render_scene_text_function_signature(self):
        """render_scene_text_image function should exist (not render_subtitle_image)."""
        from services.rendering import render_scene_text_image

        # Function should exist with new name
        assert callable(render_scene_text_image)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
