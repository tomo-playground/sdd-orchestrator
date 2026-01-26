"""Rendering service for subtitles, overlays, and post frames.

Handles all visual composition and text rendering.
"""

from __future__ import annotations

import io
import os
import pathlib
import random
import re
import textwrap
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from config import ASSETS_DIR, AVATAR_DIR, OVERLAY_DIR


def _get_assets_dir() -> pathlib.Path:
    return ASSETS_DIR


def _get_avatar_dir() -> pathlib.Path:
    return AVATAR_DIR


def _get_overlay_dir() -> pathlib.Path:
    return OVERLAY_DIR


# --- Avatar loading ---
def load_avatar_image(filename: str | None) -> Image.Image | None:
    """Load avatar image from file."""
    if not filename:
        return None
    candidate = _get_avatar_dir() / filename
    if not candidate.exists():
        return None
    try:
        return Image.open(candidate).convert("RGBA")
    except Exception:
        return None


# --- Post meta helpers ---
def _seeded_int(key: str) -> int:
    """Generate deterministic integer from string key."""
    return abs(hash(key)) % (10**9)


def _format_views(n: int) -> str:
    """Format view count for display."""
    if n >= 10000:
        return f"{n // 10000}만"
    if n >= 1000:
        return f"{n // 1000}천"
    return str(n)


def _clean_caption_title(text: str) -> str:
    """Clean caption/title for display."""
    text = re.sub(r"#\S+", "", text).strip()
    return text[:50] if len(text) > 50 else text


def _random_meta_values(rng: random.Random) -> tuple[str, str]:
    """Generate random views and timestamp."""
    views_raw = rng.randint(300, 99999)
    views = _format_views(views_raw)
    time_options = ["방금 전", "1분 전", "2분 전", "5분 전", "10분 전", "15분 전", "30분 전", "1시간 전"]
    timestamp = rng.choice(time_options)
    return views, timestamp


def _build_post_meta(
    channel_name: str,
    caption: str,
    title_text: str,
    views_override: str | None = None,
    time_override: str | None = None,
) -> dict[str, object]:
    """Build metadata for post frame."""
    seed = _seeded_int(f"{channel_name}|{caption}|{title_text}")
    name_base = (channel_name or "creator").strip()
    suffixes = ["일상", "기록", "로그", "스토리", "채널", "노트"]
    if len(name_base) < 4:
        name_base = f"{name_base}{suffixes[seed % len(suffixes)]}"
    rng = random.Random(seed)
    views, timestamp = _random_meta_values(rng)
    if views_override:
        views = views_override
    if time_override:
        timestamp = time_override
    avatar_palette = [
        (231, 198, 140),
        (210, 232, 192),
        (188, 214, 240),
        (235, 192, 208),
        (206, 196, 235),
        (240, 210, 180),
    ]
    avatar_color = avatar_palette[seed % len(avatar_palette)]
    return {
        "display_name": name_base,
        "timestamp": timestamp,
        "views": views,
        "avatar_color": avatar_color,
    }


# --- Font utilities ---
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get default Korean font."""
    font_path = str(_get_assets_dir() / "fonts" / "온글잎 박다현체.ttf")
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
        if not os.path.exists(font_path):
            font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    try:
        return ImageFont.truetype(font_path, size=size)
    except Exception:
        return ImageFont.load_default()


def _get_font_from_path(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    """Get font from specific path, fallback to default."""
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return _get_font(size)


def _draw_text_with_stroke(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke_width: int = 2,
    stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> None:
    """Draw text with stroke outline."""
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def _emoji_font(size: int) -> ImageFont.FreeTypeFont | None:
    """Load Apple Color Emoji font if available."""
    emoji_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    if not os.path.exists(emoji_path):
        return None
    try:
        return ImageFont.truetype(emoji_path, size=size)
    except Exception:
        return None


def _is_emoji_char(char: str) -> bool:
    """Check if character is an emoji."""
    return bool(re.match(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", char))


def resolve_subtitle_font_path(font_name: str | None) -> str:
    """Resolve font path for subtitles."""
    default_path = str(_get_assets_dir() / "fonts" / "온글잎 박다현체.ttf")
    if font_name:
        safe_name = os.path.basename(font_name)
        candidate = _get_assets_dir() / "fonts" / safe_name
        if candidate.exists():
            return str(candidate)
    if os.path.exists(default_path):
        return default_path
    return "/System/Library/Fonts/Supplemental/AppleGothic.ttf"


def _measure_text_with_fallback(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    emoji_font: ImageFont.FreeTypeFont | None,
) -> tuple[int, int]:
    """Measure text width/height with emoji fallback."""
    total_w = 0
    max_h = 0
    for ch in text:
        active_font = emoji_font if emoji_font and _is_emoji_char(ch) else font
        bbox = draw.textbbox((0, 0), ch, font=active_font)
        ch_w = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        total_w += ch_w
        max_h = max(max_h, ch_h)
    return total_w, max_h


def _draw_text_with_fallback(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    emoji_font: ImageFont.FreeTypeFont | None,
    fill: tuple[int, int, int, int],
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 255),
) -> None:
    """Draw text with emoji fallback support."""
    cursor_x, cursor_y = xy
    for ch in text:
        active_font = emoji_font if emoji_font and _is_emoji_char(ch) else font
        if stroke_width:
            draw.text(
                (cursor_x, cursor_y),
                ch,
                font=active_font,
                fill=fill,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
        else:
            draw.text((cursor_x, cursor_y), ch, font=active_font, fill=fill)
        bbox = draw.textbbox((0, 0), ch, font=active_font)
        cursor_x += bbox[2] - bbox[0]


# --- Subtitle rendering ---
def render_subtitle_image(
    lines: list[str],
    width: int,
    height: int,
    font_path: str,
    use_post_layout: bool,
    post_layout_metrics: dict[str, int] | None,
    font_size_override: int | None = None,
    subtitle_y_ratio: float | None = None,
) -> Image.Image:
    """Render subtitle text as transparent image.

    Args:
        lines: List of text lines to render.
        width: Canvas width.
        height: Canvas height.
        font_path: Path to font file.
        use_post_layout: Whether to use post (1:1) layout.
        post_layout_metrics: Layout metrics for post mode.
        font_size_override: Optional font size to use instead of calculated size.
        subtitle_y_ratio: Optional Y position ratio (0-1). If provided, overrides default positioning.
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    if not lines:
        return canvas

    if use_post_layout and post_layout_metrics:
        subtitle_size = font_size_override if font_size_override else int(height * 0.04)
        font = _get_font_from_path(font_path, subtitle_size)
        emoji_font = _emoji_font(subtitle_size)
        line_height = int(subtitle_size * 1.4)

        card_x = post_layout_metrics["card_x"]
        card_width = post_layout_metrics["card_width"]
        card_padding = post_layout_metrics["card_padding"]
        subtitle_y = post_layout_metrics["subtitle_y"]
        subtitle_area_height = post_layout_metrics["subtitle_area_height"]

        text_area_width = card_width - (card_padding * 2)
        text_start_y = subtitle_y + int(subtitle_area_height * 0.1)

        for idx, line in enumerate(lines[:3]):
            line_w, _ = _measure_text_with_fallback(draw, line, font, emoji_font)
            text_x = card_x + card_padding + (text_area_width - line_w) // 2
            text_y = text_start_y + idx * line_height
            _draw_text_with_fallback(
                draw,
                (text_x, text_y),
                line,
                font,
                emoji_font,
                (40, 40, 40, 255),
            )
        return canvas

    # Full layout
    subtitle_size = font_size_override if font_size_override else int(height * 0.034)
    font = _get_font_from_path(font_path, subtitle_size)
    emoji_font = _emoji_font(subtitle_size)
    line_height = int(subtitle_size * 1.45)
    line_count = len(lines)

    # Use dynamic subtitle position if provided
    if subtitle_y_ratio is not None:
        text_y_pos = int(height * subtitle_y_ratio)
    elif line_count > 1:
        text_y_pos = int(height * 0.70)
    else:
        text_y_pos = int(height * 0.72)

    for idx, line in enumerate(lines[:2]):
        line_w, _ = _measure_text_with_fallback(draw, line, font, emoji_font)
        text_x = max(0, int((width - line_w) / 2))
        _draw_text_with_fallback(
            draw,
            (text_x, text_y_pos + idx * line_height),
            line,
            font,
            emoji_font,
            (255, 255, 255, 255),
            stroke_width=5,
            stroke_fill=(0, 0, 0, 255),
        )
    return canvas


# --- Overlay rendering ---
def _draw_common_content(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: Any,  # OverlaySettings
    safe_margin: int,
    header_top: int,
    header_height: int,
    footer_top: int,
    footer_height: int,
    use_stroke: bool = False,
    text_color: tuple[int, int, int, int] = (255, 255, 255, 235),
    sub_color: tuple[int, int, int, int] = (200, 200, 200, 220),
    offset_x: int = 0,
    offset_y: int = 0,
    show_meta: bool = False,
) -> None:
    """Draw common overlay content (avatar, channel name, caption)."""
    avatar_radius = int(header_height * 0.42)
    avatar_center = (
        offset_x + safe_margin + avatar_radius + 18,
        offset_y + header_top + header_height // 2,
    )

    avatar_image = load_avatar_image(settings.avatar_file)
    if avatar_image:
        avatar_size = avatar_radius * 2
        avatar_resized = avatar_image.resize((avatar_size, avatar_size), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_resized.putalpha(mask)
        canvas.alpha_composite(
            avatar_resized,
            (avatar_center[0] - avatar_radius, avatar_center[1] - avatar_radius),
        )
    else:
        draw.ellipse(
            (
                avatar_center[0] - avatar_radius,
                avatar_center[1] - avatar_radius,
                avatar_center[0] + avatar_radius,
                avatar_center[1] + avatar_radius,
            ),
            fill=(255, 255, 255, 255),
            outline=(0, 0, 0, 255) if use_stroke or text_color == (0, 0, 0, 255) else None,
            width=2 if (use_stroke or text_color == (0, 0, 0, 255)) else 0,
        )

    name_font = _get_font(int(header_height * 0.34))
    small_font = _get_font(int(header_height * 0.24))
    caption_font = _get_font(int(footer_height * 0.22))
    avatar_font = _get_font(int(header_height * 0.32))

    name_x = avatar_center[0] + avatar_radius + 16
    name_y = offset_y + header_top + int(header_height * 0.18)

    stroke_width = 3 if use_stroke else 0
    stroke_fill = (0, 0, 0, 255)
    meta_line = f"{settings.likes_count} 조회 · 2분 전"
    meta_w = draw.textbbox((0, 0), meta_line, font=small_font)[2]
    meta_x = offset_x + width - safe_margin - meta_w
    meta_y = name_y + int(header_height * 0.5)

    if settings.posted_time:
        meta_line = f"{settings.likes_count} 조회 · {settings.posted_time}"
    if use_stroke:
        _draw_text_with_stroke(draw, (name_x, name_y), settings.channel_name, name_font, text_color, stroke_width, stroke_fill)
        if show_meta:
            _draw_text_with_stroke(draw, (meta_x, meta_y), meta_line, small_font, sub_color, stroke_width, stroke_fill)
    else:
        draw.text((name_x, name_y), settings.channel_name, fill=text_color, font=name_font)
        if show_meta:
            draw.text((meta_x, meta_y), meta_line, fill=sub_color, font=small_font)

    if not avatar_image:
        initial = (settings.channel_name.strip()[:1] or "A").upper()
        init_w, init_h = draw.textbbox((0, 0), initial, font=avatar_font)[2:]
        draw.text(
            (avatar_center[0] - init_w / 2, avatar_center[1] - init_h / 2),
            initial,
            fill=(30, 30, 30, 255),
            font=avatar_font,
        )

    caption_text = settings.caption or ""
    caption_y = offset_y + footer_top + int(footer_height * 0.2)
    caption_lines: list[str] = []
    if caption_text:
        tokens = caption_text.split()
        emojis = [token for token in tokens if not token.startswith("#")]
        hashtags = [token for token in tokens if token.startswith("#")]
        if emojis:
            caption_lines.append(" ".join(emojis[:6]))
        if hashtags:
            caption_lines.append(" ".join(hashtags[:3]))
    for idx, line in enumerate(caption_lines[:2]):
        y_pos = caption_y + idx * int(footer_height * 0.38)
        if use_stroke:
            _draw_text_with_stroke(draw, (offset_x + safe_margin + 20, y_pos), line, caption_font, text_color, stroke_width, stroke_fill)
        else:
            draw.text((offset_x + safe_margin + 20, y_pos), line, fill=text_color, font=caption_font)


def _draw_clean_overlay(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: Any,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw clean style overlay with rounded rectangles."""
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)
    header_height = int(height * 0.05)
    footer_top = int(height * 0.80)
    footer_height = int(height * 0.10)

    header_box = (offset_x + safe_margin, offset_y + header_top, offset_x + width - safe_margin, offset_y + header_top + header_height)
    footer_box = (offset_x + safe_margin, offset_y + footer_top, offset_x + width - safe_margin, offset_y + footer_top + footer_height)

    draw.rounded_rectangle(header_box, radius=28, fill=(10, 10, 10, 170))
    draw.rounded_rectangle(footer_box, radius=28, fill=(10, 10, 10, 170))

    _draw_common_content(draw, canvas, width, height, settings, safe_margin, header_top, header_height, footer_top, footer_height, offset_x=offset_x, offset_y=offset_y, show_meta=False)


def _draw_minimal_overlay(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: Any,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw minimal style overlay with stroke text."""
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)
    header_height = int(height * 0.05)
    footer_top = int(height * 0.80)
    footer_height = int(height * 0.10)

    _draw_common_content(draw, canvas, width, height, settings, safe_margin, header_top, header_height, footer_top, footer_height, use_stroke=True, offset_x=offset_x, offset_y=offset_y, show_meta=False)


def _draw_bold_overlay(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: Any,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw bold style overlay with colored backgrounds."""
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)
    header_height = int(height * 0.05)
    footer_top = int(height * 0.80)
    footer_height = int(height * 0.10)

    header_box = (offset_x + safe_margin, offset_y + header_top, offset_x + width - safe_margin, offset_y + header_top + header_height)
    footer_box = (offset_x + safe_margin, offset_y + footer_top, offset_x + width - safe_margin, offset_y + footer_top + footer_height)

    draw.rounded_rectangle(header_box, radius=16, fill=(255, 235, 59, 240), outline=(0, 0, 0, 255), width=4)
    draw.rounded_rectangle(footer_box, radius=16, fill=(255, 255, 255, 240), outline=(0, 0, 0, 255), width=4)

    _draw_common_content(draw, canvas, width, height, settings, safe_margin, header_top, header_height, footer_top, footer_height, text_color=(0, 0, 0, 255), sub_color=(60, 60, 60, 255), offset_x=offset_x, offset_y=offset_y, show_meta=False)


def _draw_overlay_header(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: Any,
    frame_style: str,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw only the header portion of overlay."""
    safe_margin = int(width * 0.06)
    header_top = int(height * 0.04)
    header_height = int(height * 0.05)

    # Draw background based on style
    if frame_style == "overlay_minimal.png":
        # Minimal: no background, stroke text only
        pass
    elif frame_style == "overlay_bold.png":
        # Bold: yellow background
        header_box = (offset_x + safe_margin, offset_y + header_top, offset_x + width - safe_margin, offset_y + header_top + header_height)
        draw.rounded_rectangle(header_box, radius=16, fill=(255, 235, 59, 240), outline=(0, 0, 0, 255), width=4)
    else:
        # Clean: dark semi-transparent background
        header_box = (offset_x + safe_margin, offset_y + header_top, offset_x + width - safe_margin, offset_y + header_top + header_height)
        draw.rounded_rectangle(header_box, radius=28, fill=(10, 10, 10, 170))

    # Draw header content (avatar + channel name)
    use_stroke = frame_style == "overlay_minimal.png"
    text_color = (0, 0, 0, 255) if frame_style == "overlay_bold.png" else (255, 255, 255, 255)

    avatar_radius = int(header_height * 0.45)
    avatar_center = (offset_x + safe_margin + avatar_radius + 12, offset_y + header_top + header_height // 2)

    avatar_image = None
    if settings.avatar_file:
        try:
            avatar_image = Image.open(settings.avatar_file).convert("RGBA")
            avatar_resized = avatar_image.resize((avatar_radius * 2, avatar_radius * 2), Image.LANCZOS)
            mask = Image.new("L", (avatar_radius * 2, avatar_radius * 2), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_radius * 2, avatar_radius * 2), fill=255)
            canvas.alpha_composite(
                avatar_resized,
                (avatar_center[0] - avatar_radius, avatar_center[1] - avatar_radius),
            )
        except Exception:
            avatar_image = None

    if not avatar_image:
        draw.ellipse(
            (
                avatar_center[0] - avatar_radius,
                avatar_center[1] - avatar_radius,
                avatar_center[0] + avatar_radius,
                avatar_center[1] + avatar_radius,
            ),
            fill=(255, 255, 255, 255),
            outline=(0, 0, 0, 255) if use_stroke or text_color == (0, 0, 0, 255) else None,
            width=2 if (use_stroke or text_color == (0, 0, 0, 255)) else 0,
        )

        avatar_font = _get_font(int(header_height * 0.32))
        initial = (settings.channel_name.strip()[:1] or "A").upper()
        init_w, init_h = draw.textbbox((0, 0), initial, font=avatar_font)[2:]
        draw.text(
            (avatar_center[0] - init_w / 2, avatar_center[1] - init_h / 2),
            initial,
            fill=(30, 30, 30, 255),
            font=avatar_font,
        )

    name_font = _get_font(int(header_height * 0.34))
    name_x = avatar_center[0] + avatar_radius + 16
    name_y = offset_y + header_top + int(header_height * 0.18)

    if use_stroke:
        _draw_text_with_stroke(draw, (name_x, name_y), settings.channel_name, name_font, text_color, 3, (0, 0, 0, 255))
    else:
        draw.text((name_x, name_y), settings.channel_name, fill=text_color, font=name_font)


def _draw_overlay_footer(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    width: int,
    height: int,
    settings: Any,
    frame_style: str,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw only the footer portion of overlay."""
    safe_margin = int(width * 0.06)
    footer_top = int(height * 0.80)
    footer_height = int(height * 0.10)

    # Draw background based on style
    if frame_style == "overlay_minimal.png":
        # Minimal: no background, stroke text only
        pass
    elif frame_style == "overlay_bold.png":
        # Bold: white background
        footer_box = (offset_x + safe_margin, offset_y + footer_top, offset_x + width - safe_margin, offset_y + footer_top + footer_height)
        draw.rounded_rectangle(footer_box, radius=16, fill=(255, 255, 255, 240), outline=(0, 0, 0, 255), width=4)
    else:
        # Clean: dark semi-transparent background
        footer_box = (offset_x + safe_margin, offset_y + footer_top, offset_x + width - safe_margin, offset_y + footer_top + footer_height)
        draw.rounded_rectangle(footer_box, radius=28, fill=(10, 10, 10, 170))

    # Draw footer content (caption)
    use_stroke = frame_style == "overlay_minimal.png"
    text_color = (0, 0, 0, 255) if frame_style == "overlay_bold.png" else (255, 255, 255, 255)

    caption_font = _get_font(int(footer_height * 0.22))
    caption_text = settings.caption or ""
    caption_y = offset_y + footer_top + int(footer_height * 0.2)
    caption_lines: list[str] = []

    if caption_text:
        tokens = caption_text.split()
        emojis = [token for token in tokens if not token.startswith("#")]
        hashtags = [token for token in tokens if token.startswith("#")]
        if emojis:
            caption_lines.append(" ".join(emojis[:6]))
        if hashtags:
            caption_lines.append(" ".join(hashtags[:3]))

    for idx, line in enumerate(caption_lines[:2]):
        y_pos = caption_y + idx * int(footer_height * 0.38)
        if use_stroke:
            _draw_text_with_stroke(draw, (offset_x + safe_margin + 20, y_pos), line, caption_font, text_color, 3, (0, 0, 0, 255))
        else:
            draw.text((offset_x + safe_margin + 20, y_pos), line, fill=text_color, font=caption_font)


def create_overlay_header(
    settings: Any,  # OverlaySettings
    width: int,
    height: int,
    output_path: pathlib.Path,
    layout_style: str = "full",
) -> None:
    """Create overlay header image (top portion only)."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    offset_x = 0
    offset_y = 0
    frame_w = width
    frame_h = height
    if layout_style == "post":
        frame_w = int(width * 0.8)
        frame_h = int(height * 0.7)
        offset_x = int(width * 0.05)
        offset_y = (height - frame_h) // 2

    _draw_overlay_header(draw, canvas, frame_w, frame_h, settings, settings.frame_style, offset_x, offset_y)
    canvas.save(output_path, "PNG")


def create_overlay_footer(
    settings: Any,  # OverlaySettings
    width: int,
    height: int,
    output_path: pathlib.Path,
    layout_style: str = "full",
) -> None:
    """Create overlay footer image (bottom portion only)."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    offset_x = 0
    offset_y = 0
    frame_w = width
    frame_h = height
    if layout_style == "post":
        frame_w = int(width * 0.8)
        frame_h = int(height * 0.7)
        offset_x = int(width * 0.05)
        offset_y = (height - frame_h) // 2

    _draw_overlay_footer(draw, canvas, frame_w, frame_h, settings, settings.frame_style, offset_x, offset_y)
    canvas.save(output_path, "PNG")


def create_overlay_image(
    settings: Any,  # OverlaySettings
    width: int,
    height: int,
    output_path: pathlib.Path,
    layout_style: str = "full",
) -> None:
    """Create overlay image with channel info and caption."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    offset_x = 0
    offset_y = 0
    frame_w = width
    frame_h = height
    if layout_style == "post":
        frame_w = int(width * 0.8)
        frame_h = int(height * 0.7)
        offset_x = int(width * 0.05)
        offset_y = (height - frame_h) // 2

    if settings.frame_style == "overlay_minimal.png":
        _draw_minimal_overlay(draw, canvas, frame_w, frame_h, settings, offset_x, offset_y)
    elif settings.frame_style == "overlay_bold.png":
        _draw_bold_overlay(draw, canvas, frame_w, frame_h, settings, offset_x, offset_y)
    else:
        _draw_clean_overlay(draw, canvas, frame_w, frame_h, settings, offset_x, offset_y)

    canvas.save(output_path, "PNG")


def resolve_overlay_frame(
    settings: Any,  # OverlaySettings
    width: int,
    height: int,
    output_path: pathlib.Path,
    layout_style: str = "full",
) -> None:
    """Resolve and create overlay frame."""
    known_styles = {"overlay_minimal.png", "overlay_clean.png", "overlay_bold.png"}
    if settings.frame_style not in known_styles:
        frame_dir = _get_overlay_dir()
        candidate = frame_dir / settings.frame_style
        if candidate.exists():
            try:
                frame = Image.open(candidate).convert("RGBA")
                if frame.size != (width, height):
                    frame = frame.resize((width, height), Image.LANCZOS)
                frame.save(output_path, "PNG")
                return
            except Exception:
                pass
    create_overlay_image(settings, width, height, output_path, layout_style)


def calculate_post_layout_metrics(width: int, height: int) -> dict[str, int]:
    """Calculate layout metrics for post-style frames.

    Shared between compose_post_frame and video filter building.
    Returns a dict with all positioning and sizing values.
    """
    card_offset_y = int(height * 0.04)
    card_width = int(width * 0.88)
    card_height = int(height * 0.86)
    card_padding = int(card_width * 0.04)
    header_height = int(card_height * 0.055)
    subtitle_area_height = int(card_height * 0.18)
    action_bar_height = int(card_height * 0.045)
    caption_height = int(card_height * 0.13)

    card_x = (width - card_width) // 2
    card_y = max(0, (height - card_height) // 2 + card_offset_y - int(height * 0.05))

    inner_width = card_width - (card_padding * 2)
    inner_height = card_height - (
        card_padding * 2 + header_height + subtitle_area_height +
        action_bar_height + caption_height
    )
    image_area = min(inner_width, inner_height)
    image_area = max(image_area, int(card_width * 0.45))
    image_area = int(image_area * 0.98)

    image_x = card_x + card_padding
    subtitle_y = card_y + card_padding + header_height
    image_y = subtitle_y + subtitle_area_height

    return {
        "card_width": card_width,
        "card_height": card_height,
        "card_padding": card_padding,
        "card_x": card_x,
        "card_y": card_y,
        "header_height": header_height,
        "subtitle_area_height": subtitle_area_height,
        "action_bar_height": action_bar_height,
        "caption_height": caption_height,
        "image_area": image_area,
        "image_x": image_x,
        "image_y": image_y,
        "subtitle_y": subtitle_y,
    }


def compose_post_frame(
    image_bytes: bytes,
    width: int,
    height: int,
    channel_name: str,
    caption: str,
    subtitle_text: str,
    font_path: str,
    avatar_file: str | None = None,
    views_override: str | None = None,
    time_override: str | None = None,
) -> Image.Image:
    """Compose Instagram-style post frame."""
    # Get layout metrics from shared function
    metrics = calculate_post_layout_metrics(width, height)
    card_width = metrics["card_width"]
    card_height = metrics["card_height"]
    card_padding = metrics["card_padding"]
    card_x = metrics["card_x"]
    card_y = metrics["card_y"]
    header_height = metrics["header_height"]
    action_bar_height = metrics["action_bar_height"]
    image_area = metrics["image_area"]
    image_x = metrics["image_x"]
    image_y = metrics["image_y"]

    image = Image.open(io.BytesIO(image_bytes))
    image_rgb = image.convert("RGB")
    background = ImageOps.fit(image_rgb, (width, height), Image.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=30)).convert("RGBA")
    background.alpha_composite(Image.new("RGBA", (width, height), (0, 0, 0, 20)))

    radius = int(card_width * 0.06)
    card = Image.new("RGBA", (card_width, card_height), (255, 255, 255, 245))
    mask = Image.new("L", (card_width, card_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, card_width, card_height), radius=radius, fill=255)
    card.putalpha(mask)
    background.alpha_composite(card, (card_x, card_y))

    # Dynamic cropping strategy:
    # If image is significantly taller than square (aspect ratio < 0.9), use TOP alignment (0.5, 0.0) to preserve head.
    # Otherwise (square or landscape), use CENTER alignment (0.5, 0.5).
    img_w, img_h = image_rgb.size
    aspect_ratio = img_w / img_h
    centering = (0.5, 0.0) if aspect_ratio < 0.85 else (0.5, 0.5)

    inner = ImageOps.fit(image_rgb, (image_area, image_area), Image.LANCZOS, centering=centering).convert("RGBA")
    background.alpha_composite(inner, (image_x, image_y))

    draw = ImageDraw.Draw(background)
    base_post_font = int(height * 0.022)
    name_font_size = base_post_font
    meta_font_size = max(10, int(base_post_font * 0.85))
    caption_font_size = max(10, int(base_post_font * 0.9))
    name_font = _get_font_from_path(font_path, name_font_size)
    meta_font = _get_font_from_path(font_path, meta_font_size)
    caption_font = _get_font_from_path(font_path, caption_font_size)

    meta_source = _build_post_meta(channel_name, caption, subtitle_text, views_override=views_override, time_override=time_override)
    display_name = meta_source["display_name"]
    timestamp = meta_source["timestamp"]
    views = meta_source["views"]
    avatar_color = meta_source["avatar_color"]

    # Header: avatar + channel name
    profile_radius = int(card_height * 0.022)
    profile_center = (card_x + card_padding + profile_radius, card_y + card_padding + int(header_height * 0.5))
    avatar_image = load_avatar_image(avatar_file)
    if avatar_image:
        avatar_size = profile_radius * 2
        avatar_resized = avatar_image.resize((avatar_size, avatar_size), Image.LANCZOS).convert("RGBA")
        avatar_mask = Image.new("L", (avatar_size, avatar_size), 0)
        avatar_mask_draw = ImageDraw.Draw(avatar_mask)
        avatar_mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_resized.putalpha(avatar_mask)
        background.alpha_composite(avatar_resized, (profile_center[0] - profile_radius, profile_center[1] - profile_radius))
    else:
        draw.ellipse(
            (profile_center[0] - profile_radius, profile_center[1] - profile_radius, profile_center[0] + profile_radius, profile_center[1] + profile_radius),
            fill=avatar_color,
            outline=(255, 255, 255),
            width=2,
        )
        initial = (str(display_name).strip()[:1] or "A").upper()
        init_font = _get_font_from_path(font_path, int(profile_radius * 1.2))
        text_w, text_h = draw.textbbox((0, 0), initial, font=init_font)[2:]
        draw.text((profile_center[0] - text_w / 2, profile_center[1] - text_h / 2), initial, fill=(80, 60, 40), font=init_font)

    name_x = profile_center[0] + profile_radius + int(card_width * 0.02)
    name_y = profile_center[1] - int(name_font_size * 0.5)
    draw.text((name_x, name_y), display_name, fill=(30, 30, 30), font=name_font)

    # Action bar
    action_y = image_y + image_area + int(card_padding * 0.5)
    icon_spacing = int(card_width * 0.08)
    icons_left = ["♡", "💬", "➤"]
    icons_right = ["🔖"]

    icon_x = card_x + card_padding
    for icon in icons_left:
        draw.text((icon_x, action_y), icon, fill=(50, 50, 50), font=meta_font)
        icon_x += icon_spacing

    bookmark_x = card_x + card_width - card_padding - int(icon_spacing * 0.5)
    for icon in icons_right:
        draw.text((bookmark_x, action_y), icon, fill=(50, 50, 50), font=meta_font)

    # Caption area
    cap_x = card_x + card_padding
    cap_y = action_y + int(action_bar_height * 1.2)

    likes_text = f"좋아요 {views}개"
    likes_font = _get_font_from_path(font_path, int(meta_font_size * 1.0))
    draw.text((cap_x, cap_y), likes_text, fill=(30, 30, 30), font=likes_font)
    cap_y += int(meta_font_size * 1.8)

    caption_text = caption.strip()
    hashtags_line = ""
    main_caption = ""
    if caption_text:
        remaining = re.sub(r"#([^\u200b\u200c#]+)", "", caption_text).strip()
        hashtag_matches = re.findall(r"#([^\u200b\u200c#]+)", caption_text)
        if hashtag_matches:
            hashtags_line = " ".join([f"#{tag.strip()}" for tag in hashtag_matches[:4]])
        if remaining:
            main_caption = remaining

    if main_caption:
        caption_line = f"{display_name} {main_caption}"
        max_chars = max(20, int(card_width * 0.08))
        wrapped = textwrap.wrap(caption_line, width=max_chars)[:2]
        for line in wrapped:
            draw.text((cap_x, cap_y), line, fill=(40, 40, 40), font=caption_font)
            cap_y += int(caption_font_size * 1.4)

    if hashtags_line:
        draw.text((cap_x, cap_y), hashtags_line, fill=(0, 55, 107), font=meta_font)
        cap_y += int(meta_font_size * 1.6)

    time_y = card_y + card_height - card_padding - int(meta_font_size * 1.2)
    draw.text((cap_x, time_y), timestamp, fill=(130, 130, 130), font=meta_font)

    return background.convert("RGB")


def apply_post_overlay_mask(overlay_path: pathlib.Path, width: int, height: int) -> None:
    """Apply rounded rectangle mask to overlay for post layout."""
    try:
        overlay = Image.open(overlay_path).convert("RGBA")
    except Exception:
        return

    card_width = int(width * 0.88)
    card_height = int(height * 0.86)
    radius = int(card_width * 0.06)
    card_x = (width - card_width) // 2
    card_y = max(0, (height - card_height) // 2 + int(height * 0.04) - int(height * 0.05))

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((card_x, card_y, card_x + card_width, card_y + card_height), radius=radius, fill=255)
    base_alpha = overlay.getchannel("A")
    non_black = ImageOps.grayscale(overlay.convert("RGB")).point(lambda v: 0 if v < 5 else 255)
    alpha = ImageChops.multiply(base_alpha, non_black)
    overlay.putalpha(ImageChops.multiply(alpha, mask))
    overlay.save(overlay_path, "PNG")
