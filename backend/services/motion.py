"""Ken Burns effect module for video motion effects.

Provides presets and FFmpeg zoompan filter generation for
smooth pan and zoom effects on static images.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

KenBurnsPresetName = Literal[
    "none",
    "slow_zoom",
    "zoom_in_center",
    "zoom_out_center",
    "pan_left",
    "pan_right",
    "pan_up",
    "pan_down",
    "zoom_pan_left",
    "zoom_pan_right",
    "pan_up_vertical",
    "pan_down_vertical",
    "zoom_in_bottom",
    "zoom_in_top",
    "pan_zoom_up",
    "pan_zoom_down",
    "random",
]


@dataclass
class KenBurnsParams:
    """Parameters for a Ken Burns effect."""

    zoom_start: float = 1.0
    zoom_end: float = 1.0
    x_start: float = 0.5  # 0.0=left, 0.5=center, 1.0=right
    x_end: float = 0.5
    y_start: float = 0.5  # 0.0=top, 0.5=center, 1.0=bottom
    y_end: float = 0.5


# Preset definitions
PRESETS: dict[str, KenBurnsParams] = {
    "none": KenBurnsParams(),
    "slow_zoom": KenBurnsParams(zoom_start=1.0, zoom_end=1.08),
    "zoom_in_center": KenBurnsParams(zoom_start=1.0, zoom_end=1.15),
    "zoom_out_center": KenBurnsParams(zoom_start=1.15, zoom_end=1.0),
    "pan_left": KenBurnsParams(x_start=0.3, x_end=0.7),
    "pan_right": KenBurnsParams(x_start=0.7, x_end=0.3),
    "pan_up": KenBurnsParams(y_start=0.6, y_end=0.4),
    "pan_down": KenBurnsParams(y_start=0.4, y_end=0.6),
    "zoom_pan_left": KenBurnsParams(zoom_start=1.0, zoom_end=1.12, x_start=0.3, x_end=0.7),
    "zoom_pan_right": KenBurnsParams(zoom_start=1.0, zoom_end=1.12, x_start=0.7, x_end=0.3),
    # Full Layout (9:16 vertical) optimized presets
    "pan_up_vertical": KenBurnsParams(y_start=0.7, y_end=0.3),
    "pan_down_vertical": KenBurnsParams(y_start=0.3, y_end=0.7),
    "zoom_in_bottom": KenBurnsParams(zoom_start=1.0, zoom_end=1.2, y_start=0.6, y_end=0.5),
    "zoom_in_top": KenBurnsParams(zoom_start=1.0, zoom_end=1.2, y_start=0.4, y_end=0.5),
    "pan_zoom_up": KenBurnsParams(zoom_start=1.0, zoom_end=1.15, y_start=0.7, y_end=0.3),
    "pan_zoom_down": KenBurnsParams(zoom_start=1.15, zoom_end=1.0, y_start=0.3, y_end=0.7),
}

# Presets eligible for random selection (excludes 'none', 'slow_zoom', 'random')
RANDOM_ELIGIBLE = [
    "zoom_in_center",
    "zoom_out_center",
    "pan_left",
    "pan_right",
    "pan_up",
    "pan_down",
    "zoom_pan_left",
    "zoom_pan_right",
    "pan_up_vertical",
    "pan_down_vertical",
    "zoom_in_bottom",
    "zoom_in_top",
    "pan_zoom_up",
    "pan_zoom_down",
]


def get_preset(name: str) -> KenBurnsParams:
    """Get a preset by name, defaulting to 'none' if not found."""
    return PRESETS.get(name, PRESETS["none"])


def get_random_preset(seed: int | None = None) -> tuple[str, KenBurnsParams]:
    """Get a random preset from the eligible list.

    Args:
        seed: Optional seed for reproducibility

    Returns:
        Tuple of (preset_name, params)
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    name = rng.choice(RANDOM_ELIGIBLE)
    return name, PRESETS[name]


def build_zoompan_filter(
    params: KenBurnsParams,
    width: int,
    height: int,
    frames: int,
    intensity: float = 1.0,
    fps: int = 25,
) -> str:
    """Build FFmpeg zoompan filter string from Ken Burns parameters.

    Args:
        params: Ken Burns effect parameters
        width: Output width
        height: Output height
        frames: Total number of frames
        intensity: Effect intensity multiplier (0.5 to 2.0)
        fps: Frames per second

    Returns:
        FFmpeg zoompan filter string
    """
    # Clamp intensity
    intensity = max(0.5, min(intensity, 2.0))

    # Calculate zoom with intensity
    z_start = params.zoom_start
    z_end = params.zoom_end
    z_delta = (z_end - z_start) * intensity
    z_end_adj = z_start + z_delta

    # Calculate pan with intensity (relative to center)
    x_start = params.x_start
    x_end = params.x_end
    x_delta = (x_end - x_start) * intensity
    x_end_adj = x_start + x_delta

    y_start = params.y_start
    y_end = params.y_end
    y_delta = (y_end - y_start) * intensity
    y_end_adj = y_start + y_delta

    # Build zoom expression
    # z = z_start + (z_end - z_start) * (on / frames)
    z_expr = f"({z_start}+{z_end_adj - z_start}*on/{frames})"

    # Build position expressions
    # x = (iw - iw/zoom) * x_ratio, interpolated from start to end
    # The position is calculated as offset from top-left
    x_ratio_expr = f"({x_start}+{x_end_adj - x_start}*on/{frames})"
    y_ratio_expr = f"({y_start}+{y_end_adj - y_start}*on/{frames})"

    x_expr = f"(iw-iw/zoom)*{x_ratio_expr}"
    y_expr = f"(ih-ih/zoom)*{y_ratio_expr}"

    return f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={width}x{height}:fps={fps}"


VALID_PRESET_NAMES: set[str] = set(PRESETS.keys()) - {"random"}

# Emotion/narrative → Ken Burns preset mapping
EMOTION_MOTION_MAP: dict[str, list[str]] = {
    # Positive / upward
    "happy": ["zoom_in_center", "pan_zoom_up"],
    "joy": ["zoom_in_center", "pan_zoom_up"],
    "hopeful": ["zoom_in_top", "pan_up"],
    "excited": ["zoom_pan_left", "zoom_pan_right"],
    "proud": ["zoom_in_bottom", "pan_zoom_up"],
    # Negative / downward
    "sad": ["zoom_out_center", "pan_down_vertical"],
    "melancholy": ["zoom_out_center", "pan_down"],
    "lonely": ["zoom_out_center", "pan_down_vertical"],
    "fearful": ["zoom_in_center", "pan_down"],
    "anxious": ["zoom_in_center", "pan_left"],
    # Tension / conflict
    "angry": ["zoom_in_center", "zoom_in_bottom"],
    "frustrated": ["zoom_pan_left", "zoom_pan_right"],
    "tense": ["zoom_in_center", "pan_up_vertical"],
    "nervous": ["zoom_in_center", "pan_left"],
    # Calm / reflective
    "calm": ["slow_zoom", "pan_right"],
    "nostalgic": ["zoom_out_center", "pan_right"],
    "peaceful": ["slow_zoom", "pan_down_vertical"],
    "reflective": ["zoom_out_center", "pan_up"],
    # Narrative function
    "hook": ["zoom_in_center", "zoom_in_bottom"],
    "climax": ["zoom_in_center", "zoom_in_top"],
    "resolution": ["zoom_out_center", "pan_down_vertical"],
    "rising": ["pan_zoom_up", "zoom_pan_right"],
    # Determination / strength
    "determined": ["zoom_in_bottom", "pan_zoom_up"],
    "confident": ["zoom_in_center", "pan_up"],
    "surprised": ["zoom_in_center", "zoom_in_top"],
}


def suggest_ken_burns_preset(emotion: str | None, seed: int = 0) -> str:
    """Suggest a Ken Burns preset based on emotion/narrative context.

    Returns a preset name from EMOTION_MOTION_MAP, or a random one if unknown.
    """
    if not emotion:
        return get_random_preset(seed)[0]
    candidates = EMOTION_MOTION_MAP.get(emotion.lower())
    if not candidates:
        return get_random_preset(seed)[0]
    rng = random.Random(seed)
    return rng.choice(candidates)


def resolve_preset_name(ken_burns_preset: str | None) -> str:
    """Resolve the effective preset name.

    Args:
        ken_burns_preset: Ken Burns preset name

    Returns:
        Resolved preset name (defaults to 'none')
    """
    if ken_burns_preset and ken_burns_preset != "none":
        return ken_burns_preset
    return "none"
