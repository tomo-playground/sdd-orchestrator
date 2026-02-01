"""Video utility functions.

Standalone helpers used by the video pipeline: filename sanitization,
BGM resolution, speed/duration calculations, and TTS text cleaning.
"""

from __future__ import annotations

import hashlib
import random
import re
import time
from pathlib import Path

from config import logger
from services.storage import get_storage


def sanitize_filename(name: str, max_length: int = 40) -> str:
    """Sanitize name for use in filenames.

    Args:
        name: Raw name from request
        max_length: Maximum length of sanitized name

    Returns:
        Safe filename-friendly name
    """
    safe_name = re.sub(r"[^\w\uac00-\ud7a3]+", "_", name).strip("_")
    if not safe_name:
        safe_name = "my_shorts"
    return safe_name[:max_length]


def resolve_bgm_file(
    bgm_file: str | None,
    seed: int | None = None,
) -> str | None:
    """Resolve BGM filename, supporting 'random' selection.

    Args:
        bgm_file: BGM filename or 'random' for random selection
        seed: Optional seed for reproducible random selection

    Returns:
        Resolved BGM filename (storage key suffix) or None
    """
    if not bgm_file or not bgm_file.strip():
        return None

    # Check for random selection (case-insensitive)
    if bgm_file.lower() == "random":
        # Find all mp3 files in shared/audio/ prefix
        prefix = "shared/audio/"
        storage = get_storage()
        all_keys = storage.list_prefix(prefix)
        mp3_keys = [k for k in all_keys if k.lower().endswith(".mp3")]

        if not mp3_keys:
            logger.warning(f"[BGM Resolve] No MP3 files found in {prefix}")
            return None

        # Select random key
        rng = random.Random(seed) if seed is not None else random.Random()
        selected_key = rng.choice(mp3_keys)
        filename = Path(selected_key).name
        logger.info(f"Random BGM selected: {filename} (from {selected_key})")
        return filename

    return bgm_file


def generate_video_filename(
    safe_title: str,
    layout_style: str,
    timestamp: int | None = None,
) -> str:
    """Generate a unique video filename.

    Args:
        safe_title: Sanitized storyboard title
        layout_style: "post" or "full"
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Unique video filename with hash
    """
    if timestamp is None:
        timestamp = int(time.time())
    layout_tag = "post" if layout_style == "post" else "full"
    hash_seed = f"{safe_title}|{layout_tag}|{timestamp}"
    hash_value = hashlib.sha1(hash_seed.encode("utf-8")).hexdigest()[:12]
    return f"{safe_title}_{layout_tag}_{hash_value}.mp4"


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
    scenes: list,
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

    Removes special characters and normalizes text for natural TTS reading.

    Args:
        raw_script: Raw script text

    Returns:
        Cleaned script text optimized for TTS
    """
    text = raw_script

    # Normalize Unicode characters
    text = text.replace("\u2026", "...")  # Ellipsis to periods
    text = text.replace("\u2014", ", ")   # Em-dash to comma
    text = text.replace("\u2013", ", ")   # En-dash to comma
    text = text.replace("\u300c", "")     # Japanese quotes
    text = text.replace("\u300d", "")
    text = text.replace("\u300e", "")
    text = text.replace("\u300f", "")

    # Remove problematic characters while keeping common punctuation and CJK
    text = re.sub(
        r"[^\w\s.,!?/\"':;~\uac00-\ud7a3a-zA-Z\u3041-\u3094\u30a1-\u30f4\u30fc\u3005\u3006\u3024\u4e00-\u9fff+\-=\u00d7\u00f7\u00b2\u00b3\u00b9\u2070()%<>]",
        "",
        text,
    )

    # Normalize multiple punctuation for natural pauses
    text = re.sub(r"\.{2,}", ".", text)     # ... -> .
    text = re.sub(r"!{2,}", "!", text)      # !!! -> !
    text = re.sub(r"\?{2,}", "?", text)     # ??? -> ?
    text = re.sub(r"\s+", " ", text)        # Multiple spaces -> single

    return text.strip()
