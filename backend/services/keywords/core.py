from __future__ import annotations

import re
from pathlib import Path

from config import CACHE_DIR, logger

# --- Lazy imports for circular dependency avoidance ---
_split_prompt_tokens = None
_normalize_prompt_tokens = None


def _get_cache_dir() -> Path:
    return CACHE_DIR


def _get_logger():
    return logger


def _get_split_prompt_tokens():
    global _split_prompt_tokens
    if _split_prompt_tokens is None:
        from services.prompt import split_prompt_tokens
        _split_prompt_tokens = split_prompt_tokens
    return _split_prompt_tokens


def _get_normalize_prompt_tokens():
    global _normalize_prompt_tokens
    if _normalize_prompt_tokens is None:
        from services.prompt import normalize_prompt_tokens
        _normalize_prompt_tokens = normalize_prompt_tokens
    return _normalize_prompt_tokens


# --- Ignore list (tokens to filter out from prompts) ---
IGNORE_TOKENS = frozenset([
    "nsfw", "nude", "uncensored", "cleavage", "text", "watermark",
    "signature", "logo", "username", "artist_name", "copyright",
    "low_quality", "worst_quality", "normal_quality", "bad_quality",
    "bad_anatomy", "bad_hands", "missing_fingers", "extra_digits",
    "fewer_digits", "extra_limbs", "cloned_face", "mutated",
    "deformed", "disfigured", "ugly", "blur", "blurry",
    "jpeg_artifacts", "cropped", "out_of_frame", "highres", "absurdres",
])

# Tags to skip (not useful for prompts or sensitive)
SKIP_TAGS = frozenset([
    # Anatomy
    "breasts", "large_breasts", "medium_breasts", "small_breasts", "huge_breasts",
    "collarbone", "thighs", "thick_thighs", "navel", "midriff", "cleavage",
    "ass", "sideboob", "underboob", "nipples", "areolae", "crotch",
    "groin", "armpits", "bare_shoulders",
    # Meta tags
    "female_focus", "solo_focus", "no_humans",
    "virtual_youtuber", "vtuber", "commentary", "translation",
    "border", "letterboxed", "pillarboxed",
    "gradient", "scan", "screencap", "official_art",
    # Sensitive subjects
    "child", "male_child", "female_child", "young", "loli", "shota",
    "aged_down", "aged_up",
    # Character-specific names (not in our LoRA library)
    "watson_amelia", "hatsune_miku",
    # Copyright tags
    "vocaloid", "fate", "genshin_impact", "blue_archive",
    # Too vague or redundant
    "girl", "boy", "woman", "man", "female", "male",
    "anime", "manga", "illustration",
])


def normalize_prompt_token(token: str) -> str:
    """Normalize a single prompt token for comparison/matching.
    Preserves underscore format (Danbooru standard).
    Strips parentheses and SD weights (e.g., '(tag:1.2)').
    """
    cleaned = token.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return ""
    
    # Remove nesting parentheses: (((tag))) -> tag
    cleaned = re.sub(r"^[()]+", "", cleaned)
    cleaned = re.sub(r"[()]+$", "", cleaned)
    
    # Remove weights: tag:1.2 -> tag
    cleaned = re.sub(r":[0-9.]*$", "", cleaned)
    
    return cleaned.strip().lower().replace(" ", "_")
