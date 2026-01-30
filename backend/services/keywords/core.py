from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

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


# --- DB-driven tag filters (loaded on startup) ---
class TagFilterCache:
    """Cache for ignore/skip tags loaded from database."""

    _ignore_tokens: frozenset[str] = frozenset()
    _skip_tags: frozenset[str] = frozenset()
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load tag filters from database."""
        if cls._initialized:
            return

        try:
            from models import TagFilter

            # Load ignore tokens
            ignore_filters = db.query(TagFilter).filter(
                TagFilter.filter_type == 'ignore',
                TagFilter.active == True
            ).all()
            cls._ignore_tokens = frozenset(f.tag_name for f in ignore_filters)

            # Load skip tags
            skip_filters = db.query(TagFilter).filter(
                TagFilter.filter_type == 'skip',
                TagFilter.active == True
            ).all()
            cls._skip_tags = frozenset(f.tag_name for f in skip_filters)

            cls._initialized = True
            logger.info(f"✅ [TagFilter] Loaded {len(cls._ignore_tokens)} ignore tokens, {len(cls._skip_tags)} skip tags")
        except Exception as e:
            logger.error(f"❌ [TagFilter] Failed to initialize: {e}")
            # Fallback to empty sets
            cls._ignore_tokens = frozenset()
            cls._skip_tags = frozenset()

    @classmethod
    def get_ignore_tokens(cls) -> frozenset[str]:
        """Get the set of tokens to ignore."""
        return cls._ignore_tokens

    @classmethod
    def get_skip_tags(cls) -> frozenset[str]:
        """Get the set of tags to skip."""
        return cls._skip_tags

    @classmethod
    def refresh(cls, db: Session):
        """Refresh filters from database."""
        cls._initialized = False
        cls.initialize(db)


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
