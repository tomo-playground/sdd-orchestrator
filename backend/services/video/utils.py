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

# Pre-compiled regex for _expand_korean_numbers (avoid recompile per call)
_KOREAN_COUNTERS = (
    "천만원|백만원|만원|천원|백원|"
    "원|개|명|번|살|층|년|월|일|시|분|초|권|장|편|곡|병|잔|통|벌|"
    "만|억|조|kg|km|cm|mm|ml|g|%"
)
_KOREAN_NUMBER_RE = re.compile(rf"(\d+)({_KOREAN_COUNTERS})")


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
    # Increased padding (0.8s) to account for:
    # 1. Transition delay (wait for crossfade to finish)
    # 2. Natural pause after sentence
    tts_padding = 0.8 / clamped
    return transition_dur, tts_padding, clamped


def calculate_scene_durations(
    scenes: list,
    tts_valid: list[bool],
    tts_durations: list[float],
    speed_multiplier: float,
    tts_padding: float,
    transition_dur: float = 0.0,
) -> list[float]:
    """Calculate final duration for each scene.

    Args:
        scenes: List of video scenes
        tts_valid: Whether TTS was generated for each scene
        tts_durations: TTS audio duration for each scene
        speed_multiplier: Speed factor
        tts_padding: Extra padding after TTS
        transition_dur: Crossfade duration between scenes. Non-last scenes
            need extra time because adelay shifts audio start and acrossfade
            consumes the tail.

    Returns:
        List of scene durations in seconds
    """
    num_scenes = len(scenes)
    durations: list[float] = []
    for i, scene in enumerate(scenes):
        base_duration = (getattr(scene, "duration", 3) or 3) / speed_multiplier

        # Use agent-designed padding if available
        h_pad = getattr(scene, "head_padding", 0.0) or 0.0
        t_pad = getattr(scene, "tail_padding", 0.0) or 0.0

        if tts_valid[i] and tts_durations[i] > 0:
            # adelay shifts audio start by (transition_dur + h_pad).
            # acrossfade consumes the last transition_dur of non-last scenes.
            # Add transition_dur to compensate so TTS finishes before fade-out.
            xfade_compensation = transition_dur if i < num_scenes - 1 else 0.0
            total_tts_dur = h_pad + tts_durations[i] + t_pad + tts_padding + xfade_compensation
            base_duration = max(base_duration, total_tts_dur)

        durations.append(base_duration)
    return durations


def _strip_non_speech(text: str) -> str:
    """Remove stage directions, meta tags, and hashtags from script.

    Keeps actual spoken text only. Parenthetical/bracket content is treated
    as non-speech (stage directions, sound effects, visual cues).

    Examples:
        "(한숨) 힘들다..."          → "힘들다..."
        "[BGM 시작] 안녕하세요"     → "안녕하세요"
        "오늘 #일상 #직장인"        → "오늘"
        "(조용히) 괜찮아. (미소)"   → "괜찮아."
        "아... 그랬구나"            → "아... 그랬구나"  (감탄사 유지)
    """
    # 1. Remove [...] blocks (meta/visual cues)
    text = re.sub(r"\[.*?\]", "", text)
    # 2. Remove (...) blocks (stage directions/SFX)
    text = re.sub(r"\(.*?\)", "", text)
    # 3. Remove #hashtags
    text = re.sub(r"#\w+", "", text)
    # 4. Remove *markers* (markdown emphasis used as SFX)
    text = re.sub(r"\*[^*]+\*", "", text)
    # 5. Collapse leftover whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_speakable_content(raw_script: str) -> bool:
    """Check if a script contains enough content to be spoken by TTS.

    Applies _strip_non_speech first, then checks:
    1. At least one word character exists
    2. Word character count >= TTS_MIN_SPEAKABLE_CHARS (default 2)

    Short exclamations like "네?" (1 char) produce TTS < 0.5s which always
    fails the TTS_MIN_DURATION_SEC (1.0s) check, wasting 3 retry attempts.
    These are better served by silence + subtitle overlay.

    Returns:
        True if the script has enough word characters for meaningful TTS.
    """
    from config import TTS_MIN_SPEAKABLE_CHARS

    if not raw_script or not raw_script.strip():
        return False
    text = _strip_non_speech(raw_script)
    # Count Unicode word characters (Korean, Japanese, Chinese, Latin, digits)
    word_chars = re.findall(r"\w", text)
    return len(word_chars) >= TTS_MIN_SPEAKABLE_CHARS


def clean_script_for_tts(raw_script: str) -> str:
    """Clean script text for TTS generation.

    Removes non-speech content (stage directions, meta tags) and
    normalizes special characters for natural TTS reading.

    Args:
        raw_script: Raw script text

    Returns:
        Cleaned script text optimized for TTS
    """
    text = raw_script

    # Strip non-speech content (stage directions, hashtags, etc.)
    text = _strip_non_speech(text)

    # Normalize Unicode characters
    text = text.replace("\u2026", "...")  # Ellipsis to periods
    text = text.replace("\u2014", ", ")  # Em-dash to comma
    text = text.replace("\u2013", ", ")  # En-dash to comma
    text = text.replace("\u300c", "")  # Japanese quotes
    text = text.replace("\u300d", "")
    text = text.replace("\u300e", "")
    text = text.replace("\u300f", "")

    # Remove problematic characters while keeping common punctuation and CJK
    text = re.sub(
        r"[^\w\s.,!?/\"':;~\uac00-\ud7a3a-zA-Z\u3041-\u3094\u30a1-\u30f4\u30fc\u3005\u3006\u3024\u4e00-\u9fff+\-=\u00d7\u00f7\u00b2\u00b3\u00b9\u2070()%<>]",
        "",
        text,
    )

    # Normalize repeated punctuation
    text = re.sub(r"\.{2,}", ".", text)  # ... -> .
    text = re.sub(r"!{2,}", "!", text)  # !!! -> !
    text = re.sub(r"\?{2,}", "?", text)  # ??? -> ?
    text = re.sub(r"\s+", " ", text)  # Multiple spaces -> single

    # Convert number+Korean unit to spoken Korean (prevents TTS hang)
    text = _expand_korean_numbers(text)

    return text.strip()


def _expand_korean_numbers(text: str) -> str:
    """Expand number+unit patterns to spoken Korean for TTS.

    e.g. '3만원' -> '삼만원', '100개' -> '백개', '25일' -> '이십오일'
    """
    sino_digits = {
        "0": "영",
        "1": "일",
        "2": "이",
        "3": "삼",
        "4": "사",
        "5": "오",
        "6": "육",
        "7": "칠",
        "8": "팔",
        "9": "구",
    }
    sino_units = ["", "십", "백", "천"]
    large_units = ["", "만", "억", "조"]

    def _num_to_sino(n: int) -> str:
        if n == 0:
            return "영"
        result = ""
        s = str(n)
        length = len(s)
        for i, ch in enumerate(s):
            d = int(ch)
            if d == 0:
                continue
            pos = length - 1 - i
            large_idx = pos // 4
            small_idx = pos % 4
            digit_str = sino_digits[ch] if d != 1 or small_idx == 0 else ""
            result += digit_str + sino_units[small_idx]
            if small_idx == 0 and large_idx > 0:
                result += large_units[large_idx]
        return result or "영"

    def _replace(m: re.Match) -> str:
        num_str = m.group(1)
        unit = m.group(2)
        try:
            return _num_to_sino(int(num_str)) + unit
        except (ValueError, OverflowError):
            return m.group(0)

    return _KOREAN_NUMBER_RE.sub(_replace, text)
