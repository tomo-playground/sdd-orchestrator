"""
VRT tests for overlay rendering.

Tests the create_overlay_image function to ensure visual consistency
across different overlay styles (clean, minimal, bold).
"""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from logic import create_overlay_image
from schemas import OverlaySettings
from tests.vrt.compare import VRTComparison, pil_to_numpy


class TestOverlayRenderingFull:
    """Tests for Full layout (9:16) overlay rendering."""

    def test_overlay_clean_style(self, vrt: VRTComparison):
        """Test clean overlay style in Full layout."""
        settings = OverlaySettings(
            channel_name="test_channel",
            avatar_key="test_avatar",
            likes_count="1.2k",
            posted_time="방금 전",
            caption="테스트 캡션입니다 #shorts",
            frame_style="overlay_clean.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1920, output_path, "full")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/full_clean.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)

    def test_overlay_minimal_style(self, vrt: VRTComparison):
        """Test minimal overlay style in Full layout."""
        settings = OverlaySettings(
            channel_name="minimal_ch",
            avatar_key="minimal",
            likes_count="500",
            posted_time="1시간 전",
            caption="미니멀 스타일 테스트",
            frame_style="overlay_minimal.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1920, output_path, "full")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/full_minimal.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)

    def test_overlay_bold_style(self, vrt: VRTComparison):
        """Test bold overlay style in Full layout."""
        settings = OverlaySettings(
            channel_name="bold_channel",
            avatar_key="bold",
            likes_count="99.9k",
            posted_time="어제",
            caption="볼드한 스타일! #trending #viral",
            frame_style="overlay_bold.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1920, output_path, "full")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/full_bold.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)


class TestOverlayRenderingPost:
    """Tests for Post layout (1:1) overlay rendering."""

    def test_overlay_clean_post(self, vrt: VRTComparison):
        """Test clean overlay style in Post layout."""
        settings = OverlaySettings(
            channel_name="post_channel",
            avatar_key="post",
            likes_count="2.3k",
            posted_time="3일 전",
            caption="Post 레이아웃 테스트",
            frame_style="overlay_clean.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1080, output_path, "post")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/post_clean.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)

    def test_overlay_minimal_post(self, vrt: VRTComparison):
        """Test minimal overlay style in Post layout."""
        settings = OverlaySettings(
            channel_name="insta_style",
            avatar_key="insta",
            likes_count="10k",
            posted_time="1주일 전",
            caption="인스타 스타일 #instagram",
            frame_style="overlay_minimal.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1080, output_path, "post")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/post_minimal.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)


class TestOverlayEdgeCases:
    """Edge case tests for overlay rendering."""

    def test_overlay_long_channel_name(self, vrt: VRTComparison):
        """Test overlay with very long channel name."""
        settings = OverlaySettings(
            channel_name="very_long_channel_name_that_might_overflow",
            avatar_key="long",
            likes_count="1M",
            posted_time="한달 전",
            caption="긴 채널명 테스트",
            frame_style="overlay_clean.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1920, output_path, "full")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/full_long_name.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)

    def test_overlay_emoji_caption(self, vrt: VRTComparison):
        """Test overlay with emoji in caption."""
        settings = OverlaySettings(
            channel_name="emoji_ch",
            avatar_key="emoji",
            likes_count="5k",
            posted_time="2시간 전",
            caption="이모지 테스트! 🎉🔥✨ #emoji",
            frame_style="overlay_minimal.png",
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            create_overlay_image(settings, 1080, 1920, output_path, "full")
            result = Image.open(output_path)
            comparison = vrt.compare("overlay/full_emoji.png", result)
            assert comparison.passed, f"VRT failed: {comparison.message}"
        finally:
            output_path.unlink(missing_ok=True)
