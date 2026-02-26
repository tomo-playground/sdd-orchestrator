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


# --- DB-driven tag filters (re-exported from db_cache for backward compat) ---
from services.keywords.db_cache import TagFilterCache  # noqa: E402

# Backward compatibility: expose as module-level constants
# These will be empty until initialize() is called
IGNORE_TOKENS = TagFilterCache.get_ignore_tokens()
SKIP_TAGS = TagFilterCache.get_skip_tags()


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
    # Remove weights: tag:1.2 -> tag
    cleaned = re.sub(r":[0-9.]*$", "", cleaned)

    # Strip leading/trailing underscores and whitespace
    cleaned = cleaned.strip().strip("_")

    # Collapse multiple underscores: __day -> day, super__cool -> super_cool
    cleaned = re.sub(r"_{2,}", "_", cleaned)

    return cleaned.lower().replace(" ", "_")
