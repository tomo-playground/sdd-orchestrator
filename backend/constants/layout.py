"""
Layout Schema for Shorts Producer.

This module contains all layout-related constants extracted from logic.py.
Centralizing these values enables:
1. Easy adjustment of layouts without code changes
2. Visual regression testing against known configurations
3. Potential future support for custom themes/layouts

Usage:
    from constants.layout import FullLayout, PostLayout

    font_size = int(height * FullLayout.SUBTITLE_FONT_RATIO)
"""

from dataclasses import dataclass
from typing import Tuple


# Type aliases for clarity
RGBA = Tuple[int, int, int, int]
RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class FullLayout:
    """
    Full layout (9:16) configuration for vertical short-form videos.
    Standard resolution: 1080x1920
    """

    # === Subtitle Rendering ===
    SUBTITLE_FONT_RATIO: float = 0.034  # height * ratio = font size
    SUBTITLE_LINE_HEIGHT_RATIO: float = 1.45  # font_size * ratio = line height
    SUBTITLE_Y_SINGLE_LINE_RATIO: float = 0.72  # Y position for 1 line
    SUBTITLE_Y_MULTI_LINE_RATIO: float = 0.70  # Y position for 2+ lines
    SUBTITLE_TEXT_COLOR: RGBA = (255, 255, 255, 255)  # White
    SUBTITLE_STROKE_WIDTH: int = 5
    SUBTITLE_STROKE_COLOR: RGBA = (0, 0, 0, 255)  # Black
    SUBTITLE_MAX_LINES: int = 2

    # === Overlay Layout ===
    SAFE_MARGIN_RATIO: float = 0.06  # width * ratio
    HEADER_TOP_RATIO: float = 0.04  # height * ratio
    HEADER_HEIGHT_RATIO: float = 0.05  # height * ratio
    FOOTER_TOP_RATIO: float = 0.80  # height * ratio
    FOOTER_HEIGHT_RATIO: float = 0.10  # height * ratio

    # === Clean/Minimal Style ===
    BOX_RADIUS: int = 28
    BOX_BACKGROUND_COLOR: RGBA = (10, 10, 10, 170)  # Semi-transparent black

    # === Bold Style ===
    BOLD_BOX_RADIUS: int = 16
    BOLD_HEADER_BG_COLOR: RGBA = (255, 235, 59, 240)  # Yellow
    BOLD_FOOTER_BG_COLOR: RGBA = (255, 255, 255, 240)  # White
    BOLD_BOX_OUTLINE_COLOR: RGBA = (0, 0, 0, 255)  # Black
    BOLD_BOX_OUTLINE_WIDTH: int = 4
    BOLD_TEXT_COLOR: RGBA = (0, 0, 0, 255)  # Black
    BOLD_SUB_TEXT_COLOR: RGBA = (60, 60, 60, 255)  # Dark gray

    # === FFmpeg/Video ===
    SQUARE_IMAGE_Y_RATIO: float = 0.10  # Y position for square image
    BACKGROUND_BLUR: str = "40:20"  # boxblur filter value


@dataclass(frozen=True)
class PostLayout:
    """
    Post layout (1:1) configuration for Instagram-style square posts.
    Standard resolution: 1080x1080
    """

    # === Card Layout ===
    CARD_OFFSET_Y_RATIO: float = 0.04  # height * ratio
    CARD_WIDTH_RATIO: float = 0.88  # width * ratio
    CARD_HEIGHT_RATIO: float = 0.86  # height * ratio
    CARD_PADDING_RATIO: float = 0.04  # card_width * ratio
    CARD_RADIUS_RATIO: float = 0.06  # card_width * ratio
    CARD_BG_COLOR: RGBA = (255, 255, 255, 245)  # Near-white

    # === Background ===
    BG_OVERLAY_COLOR: RGBA = (0, 0, 0, 20)  # Slight darkening
    BG_BLUR_RADIUS: int = 30  # GaussianBlur radius

    # === Section Heights (relative to card_height) ===
    HEADER_HEIGHT_RATIO: float = 0.055
    SUBTITLE_AREA_HEIGHT_RATIO: float = 0.10
    ACTION_BAR_HEIGHT_RATIO: float = 0.045
    CAPTION_HEIGHT_RATIO: float = 0.13

    # === Profile/Avatar ===
    PROFILE_RADIUS_RATIO: float = 0.022  # card_height * ratio
    AVATAR_INITIAL_FONT_RATIO: float = 1.2  # profile_radius * ratio
    AVATAR_INITIAL_COLOR: RGB = (80, 60, 40)  # Brown

    # === Fonts (relative to height) ===
    BASE_FONT_RATIO: float = 0.022
    META_FONT_RATIO: float = 0.85  # base_font * ratio
    CAPTION_FONT_RATIO: float = 0.9  # base_font * ratio
    ICON_FONT_RATIO: float = 1.2  # base_font * ratio

    # === Text Positioning ===
    NAME_X_OFFSET_RATIO: float = 0.02  # card_width * ratio
    NAME_Y_CENTER_OFFSET: float = 0.5  # name_font_size * ratio
    ACTION_Y_PADDING_RATIO: float = 0.5  # card_padding * ratio
    ICON_SPACING_RATIO: float = 0.08  # card_width * ratio
    CAPTION_Y_OFFSET_RATIO: float = 1.2  # action_bar_height * ratio

    # === Colors ===
    CHANNEL_NAME_COLOR: RGB = (30, 30, 30)
    ICON_COLOR: RGB = (50, 50, 50)
    CAPTION_TEXT_COLOR: RGB = (40, 40, 40)
    HASHTAG_COLOR: RGB = (0, 55, 107)  # Instagram blue
    TIMESTAMP_COLOR: RGB = (130, 130, 130)  # Gray

    # === Image Area ===
    MIN_IMAGE_AREA_RATIO: float = 0.45  # card_width * ratio
    IMAGE_AREA_SCALE: float = 0.98

    # === Subtitle in Post Layout ===
    SUBTITLE_FONT_RATIO: float = 0.04  # height * ratio
    SUBTITLE_LINE_HEIGHT_RATIO: float = 1.4  # font_size * ratio
    SUBTITLE_TEXT_START_Y_RATIO: float = 0.1  # subtitle_area_height * ratio
    SUBTITLE_TEXT_COLOR: RGBA = (40, 40, 40, 255)  # Dark gray
    SUBTITLE_MAX_LINES: int = 3


@dataclass(frozen=True)
class CommonLayout:
    """
    Common layout values shared between Full and Post layouts.
    """

    # === Avatar ===
    AVATAR_RADIUS_RATIO: float = 0.42  # header_height * ratio
    AVATAR_X_OFFSET: int = 18  # pixels
    AVATAR_BG_COLOR: RGBA = (255, 255, 255, 255)  # White
    AVATAR_OUTLINE_WIDTH: int = 2
    AVATAR_FONT_RATIO: float = 0.32  # header_height * ratio
    AVATAR_INITIAL_COLOR: RGBA = (30, 30, 30, 255)  # Dark gray

    # === Fonts ===
    NAME_FONT_RATIO: float = 0.34  # header_height * ratio
    SMALL_FONT_RATIO: float = 0.24  # header_height * ratio
    CAPTION_FONT_RATIO: float = 0.22  # footer_height * ratio

    # === Text Positioning ===
    NAME_X_OFFSET: int = 16  # pixels
    NAME_Y_RATIO: float = 0.18  # header_height * ratio
    META_Y_OFFSET_RATIO: float = 0.5  # header_height * ratio
    CAPTION_Y_START_RATIO: float = 0.2  # footer_height * ratio
    CAPTION_LINE_HEIGHT_RATIO: float = 0.38  # footer_height * ratio
    CAPTION_X_OFFSET: int = 20  # pixels

    # === Text Styling ===
    TEXT_COLOR: RGBA = (255, 255, 255, 235)  # White with slight transparency
    SUB_TEXT_COLOR: RGBA = (200, 200, 200, 220)  # Light gray
    STROKE_COLOR: RGBA = (0, 0, 0, 255)  # Black
    STROKE_WIDTH: int = 3

    # === Overlay Post Mode ===
    OVERLAY_POST_FRAME_WIDTH_RATIO: float = 0.8
    OVERLAY_POST_FRAME_HEIGHT_RATIO: float = 0.7
    OVERLAY_POST_X_OFFSET_RATIO: float = 0.05


@dataclass(frozen=True)
class MotionConfig:
    """
    Motion/animation configuration for video effects.
    """

    # === Zoom Effect ===
    ZOOM_INCREMENT: float = 0.0008  # zoom += this per frame
    MAX_ZOOM_SCALE: float = 1.08  # maximum zoom level

    # === Overlay ===
    ALPHA_MULTIPLIER: float = 1.6  # overlay alpha amplification

    # === Transition ===
    DEFAULT_XFADE_DURATION: float = 0.3  # seconds
    XFADE_OFFSET: float = 0.15  # pre-offset for smoother transition


@dataclass(frozen=True)
class OverlayColors:
    """
    Color palette for overlays and UI elements.
    """

    # === Avatar Palette ===
    AVATAR_PALETTE: tuple = (
        (255, 183, 77),   # Orange
        (129, 199, 132),  # Green
        (100, 181, 246),  # Blue
        (240, 98, 146),   # Pink
        (186, 104, 200),  # Purple
        (255, 138, 128),  # Coral
    )

    # === UI Colors ===
    TRANSPARENT: RGBA = (0, 0, 0, 0)
    WHITE: RGBA = (255, 255, 255, 255)
    BLACK: RGBA = (0, 0, 0, 255)
    SEMI_BLACK: RGBA = (0, 0, 0, 128)

    # === Status Colors ===
    SUCCESS: RGB = (76, 175, 80)  # Green
    WARNING: RGB = (255, 193, 7)  # Amber
    ERROR: RGB = (244, 67, 54)  # Red


# === Convenience Functions ===

def get_full_subtitle_position(height: int, line_count: int) -> int:
    """Calculate Y position for subtitle in Full layout."""
    if line_count > 1:
        return int(height * FullLayout.SUBTITLE_Y_MULTI_LINE_RATIO)
    return int(height * FullLayout.SUBTITLE_Y_SINGLE_LINE_RATIO)


def get_post_card_dimensions(width: int, height: int) -> dict:
    """Calculate card dimensions for Post layout."""
    card_width = int(width * PostLayout.CARD_WIDTH_RATIO)
    card_height = int(height * PostLayout.CARD_HEIGHT_RATIO)
    return {
        "card_width": card_width,
        "card_height": card_height,
        "card_padding": int(card_width * PostLayout.CARD_PADDING_RATIO),
        "card_radius": int(card_width * PostLayout.CARD_RADIUS_RATIO),
        "card_x": (width - card_width) // 2,
        "card_y": (height - card_height) // 2 + int(height * PostLayout.CARD_OFFSET_Y_RATIO),
    }
