from __future__ import annotations

from typing import Any

from database import SessionLocal
from models.tag import Tag

from .core import IGNORE_TOKENS, normalize_prompt_token


def load_tags_from_db() -> dict[str, list[str]]:
    """Load tags from database grouped by default_layer."""
    db = SessionLocal()
    try:
        tags = db.query(Tag).order_by(Tag.default_layer, Tag.name).all()
        grouped: dict[str, list[str]] = {}
        for tag in tags:
            layer_key = f"layer_{tag.default_layer}"
            if layer_key not in grouped:
                grouped[layer_key] = []
            grouped[layer_key].append(tag.name)
        return grouped
    finally:
        db.close()

def load_allowed_tags_from_db() -> set[str]:
    """Load all tag names from database as allowed set."""
    db = SessionLocal()
    try:
        tags = db.query(Tag.name).all()
        return {normalize_prompt_token(t.name) for t in tags}
    finally:
        db.close()

def load_known_keywords() -> set[str]:
    """Load all known keywords from database."""
    allowed = load_allowed_tags_from_db()
    # Synonyms and effectiveness tracking are currently disabled in Pure V3 slimdown
    known = allowed.copy()
    known.update(IGNORE_TOKENS)
    return known

def load_synonyms_from_db() -> dict[str, str]:
    """Load tag synonyms (Stub for V3)."""
    return {}

def load_tag_effectiveness_map() -> dict[str, tuple[float | None, int]]:
    """Load tag effectiveness data (Stub for V3)."""
    return {}

def load_tag_effectiveness_report() -> list[dict[str, Any]]:
    """Load full effectiveness report (Stub for V3)."""
    return []

# Legacy group mappings for Gemini-friendly prompt formatting
_SCENE_GROUPS = [
    "layer_0", "layer_1", "layer_2", "layer_3", "layer_4", "layer_5",
    "layer_6", "layer_7", "layer_8", "layer_9", "layer_10", "layer_11",
    "expression", "pose", "camera", "location_indoor", "location_outdoor", "lighting", "mood", "time"
]

_DB_GROUP_TO_GEMINI_CATEGORY = {
    "layer_0": "composition",
    "layer_1": "subject",
    "layer_2": "pose",
    "layer_3": "clothing",
    "layer_4": "hair",
    "layer_5": "expression",
    "layer_6": "background",
    "expression": "expression",
    "pose": "pose",
    "camera": "camera",
    "location_indoor": "environment",
    "location_outdoor": "environment",
}
