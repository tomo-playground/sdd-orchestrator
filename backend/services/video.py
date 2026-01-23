"""Video service for video creation helpers.

Provides utility functions for video rendering pipeline.
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schemas import VideoScene


def sanitize_project_name(project_name: str, max_length: int = 40) -> str:
    """Sanitize project name for use in filenames.

    Args:
        project_name: Raw project name from request
        max_length: Maximum length of sanitized name

    Returns:
        Safe filename-friendly project name
    """
    safe_name = re.sub(r"[^\w가-힣]+", "_", project_name).strip("_")
    if not safe_name:
        safe_name = "my_shorts"
    return safe_name[:max_length]


def generate_video_filename(
    project_name: str,
    layout_style: str,
    timestamp: int | None = None,
) -> str:
    """Generate a unique video filename.

    Args:
        project_name: Sanitized project name
        layout_style: "post" or "full"
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Unique video filename with hash
    """
    if timestamp is None:
        timestamp = int(time.time())
    layout_tag = "post" if layout_style == "post" else "full"
    hash_seed = f"{project_name}|{layout_tag}|{timestamp}"
    hash_value = hashlib.sha1(hash_seed.encode("utf-8")).hexdigest()[:12]
    return f"{project_name}_{layout_tag}_{hash_value}.mp4"


def calculate_speed_params(speed_multiplier: float) -> tuple[float, float, float]:
    """Calculate timing parameters based on speed multiplier.

    Args:
        speed_multiplier: Speed factor (0.25 to 2.0)

    Returns:
        Tuple of (transition_duration, tts_padding, clamped_speed_multiplier)
    """
    clamped = max(0.25, min(speed_multiplier or 1.0, 2.0))
    transition_dur = max(0.1, 0.5 / clamped)
    tts_padding = 0.5 / clamped
    return transition_dur, tts_padding, clamped


def calculate_scene_durations(
    scenes: list["VideoScene"],
    tts_valid: list[bool],
    tts_durations: list[float],
    speed_multiplier: float,
    tts_padding: float,
) -> list[float]:
    """Calculate final duration for each scene.

    Args:
        scenes: List of video scenes
        tts_valid: Whether TTS was generated for each scene
        tts_durations: TTS audio duration for each scene
        speed_multiplier: Speed factor
        tts_padding: Extra padding after TTS

    Returns:
        List of scene durations in seconds
    """
    durations: list[float] = []
    for i, scene in enumerate(scenes):
        base_duration = (scene.duration or 3) / speed_multiplier
        if tts_valid[i] and tts_durations[i] > 0:
            base_duration = max(base_duration, tts_durations[i] + tts_padding)
        durations.append(base_duration)
    return durations


def clean_script_for_tts(raw_script: str) -> str:
    """Clean script text for TTS generation.

    Removes special characters that might cause TTS issues.

    Args:
        raw_script: Raw script text

    Returns:
        Cleaned script text
    """
    # Remove problematic characters while keeping common punctuation and CJK
    clean = re.sub(
        r"[^\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥+\-=×÷²³¹⁰()%<>]",
        "",
        raw_script
    )
    return clean.replace("'", "").strip()
