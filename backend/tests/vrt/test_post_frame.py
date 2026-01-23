"""
VRT tests for Post frame composition.

Tests the compose_post_frame function to ensure visual consistency
of the Instagram-style post layout.
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from services.rendering import compose_post_frame
from tests.vrt.compare import VRTComparison


def create_sample_image(width: int = 512, height: int = 512, color: tuple = (100, 150, 200)) -> bytes:
    """Create a sample image for testing."""
    img = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestPostFrameComposition:
    """Tests for Post frame composition."""

    def test_post_frame_basic(self, vrt: VRTComparison, sample_font_path: Path):
        """Test basic post frame composition."""
        image_bytes = create_sample_image(512, 512, (100, 120, 140))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="test_channel",
            caption="테스트 캡션입니다 #shorts #test",
            subtitle_text="자막 텍스트",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/basic.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_frame_long_caption(self, vrt: VRTComparison, sample_font_path: Path):
        """Test post frame with long caption."""
        image_bytes = create_sample_image(512, 512, (150, 100, 100))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="story_channel",
            caption="이것은 매우 긴 캡션입니다. 여러 줄에 걸쳐 표시될 수 있습니다. #longtag #verylonghashtag #test",
            subtitle_text="긴 캡션 테스트",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/long_caption.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_frame_korean_content(self, vrt: VRTComparison, sample_font_path: Path):
        """Test post frame with Korean content."""
        image_bytes = create_sample_image(512, 512, (120, 180, 120))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="한글채널",
            caption="오늘의 일상 브이로그입니다 #일상 #브이로그 #데일리",
            subtitle_text="한글 자막입니다",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/korean.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_frame_views_override(self, vrt: VRTComparison, sample_font_path: Path):
        """Test post frame with custom views count."""
        image_bytes = create_sample_image(512, 512, (200, 150, 100))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="popular_ch",
            caption="인기 영상! #viral",
            subtitle_text="조회수 테스트",
            font_path=str(sample_font_path),
            views_override="1.5M",
            time_override="2일 전",
        )

        comparison = vrt.compare("post_frame/custom_views.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_frame_no_hashtags(self, vrt: VRTComparison, sample_font_path: Path):
        """Test post frame without hashtags."""
        image_bytes = create_sample_image(512, 512, (180, 180, 180))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="simple_ch",
            caption="해시태그 없는 심플한 캡션",
            subtitle_text="심플 테스트",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/no_hashtags.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_frame_emoji_content(self, vrt: VRTComparison, sample_font_path: Path):
        """Test post frame with emoji."""
        image_bytes = create_sample_image(512, 512, (255, 200, 150))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="emoji_lover",
            caption="이모지 테스트! 🎉🔥✨💖 #emoji #fun",
            subtitle_text="이모지가 포함된 자막 😊",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/emoji.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"


class TestPostFrameDimensions:
    """Tests for different post frame dimensions."""

    def test_post_frame_square_1080(self, vrt: VRTComparison, sample_font_path: Path):
        """Test 1080x1080 square post frame."""
        image_bytes = create_sample_image(512, 512, (100, 100, 200))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=1080,
            height=1080,
            channel_name="square_ch",
            caption="1080x1080 정사각형",
            subtitle_text="정사각형 테스트",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/square_1080.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_post_frame_smaller_720(self, vrt: VRTComparison, sample_font_path: Path):
        """Test 720x720 smaller post frame."""
        image_bytes = create_sample_image(512, 512, (200, 100, 100))

        result = compose_post_frame(
            image_bytes=image_bytes,
            width=720,
            height=720,
            channel_name="small_ch",
            caption="720x720 작은 사이즈",
            subtitle_text="작은 프레임 테스트",
            font_path=str(sample_font_path),
        )

        comparison = vrt.compare("post_frame/square_720.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"
