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
    """Load tag effectiveness data from DB.

    Returns: {tag_name: (effectiveness_ratio, use_count)}
    """
    from models.tag import TagEffectiveness

    db = SessionLocal()
    try:
        rows = (
            db.query(Tag.name, TagEffectiveness.effectiveness, TagEffectiveness.use_count)
            .join(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(TagEffectiveness.use_count > 0)
            .all()
        )
        return {name: (eff, count) for name, eff, count in rows}
    finally:
        db.close()

def load_tag_effectiveness_report() -> list[dict[str, Any]]:
    """Load full effectiveness report from DB."""
    from models.tag import TagEffectiveness

    db = SessionLocal()
    try:
        rows = (
            db.query(
                Tag.name,
                Tag.id,
                TagEffectiveness.use_count,
                TagEffectiveness.match_count,
                TagEffectiveness.effectiveness,
            )
            .join(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(TagEffectiveness.use_count > 0)
            .order_by(TagEffectiveness.effectiveness.desc())
            .all()
        )
        return [
            {
                "tag_name": name,
                "tag_id": tag_id,
                "use_count": use_count,
                "match_count": match_count,
                "effectiveness": effectiveness,
            }
            for name, tag_id, use_count, match_count, effectiveness in rows
        ]
    finally:
        db.close()

# Legacy group mappings for Gemini-friendly prompt formatting
_SCENE_GROUPS = [
    "layer_0", "layer_1", "layer_2", "layer_3", "layer_4", "layer_5",
    "layer_6", "layer_7", "layer_8", "layer_9", "layer_10", "layer_11",
    "expression", "pose", "camera", "location_indoor", "location_outdoor", "lighting", "mood", "time"
]

# Maps DB layer groups → Gemini-readable category names
# Must align with v3_composition.py 12-Layer system and create_storyboard.j2 template
_DB_GROUP_TO_GEMINI_CATEGORY = {
    "layer_0": None,           # QUALITY — auto-composed, not for Gemini selection
    "layer_1": None,           # SUBJECT — auto-composed (1boy, solo, etc.)
    "layer_2": "character",    # IDENTITY — character features
    "layer_3": "body",         # BODY — body type
    "layer_4": "clothing",     # MAIN_CLOTH
    "layer_5": "clothing",     # DETAIL_CLOTH — merge with clothing
    "layer_6": "props",        # ACCESSORY — held items, worn accessories (holding_phone, etc.)
    "layer_7": "expression",   # EXPRESSION
    "layer_8": "action",       # ACTION — pose, gesture
    "layer_9": "camera",       # CAMERA — shot type, angle
    "layer_10": "environment", # ENVIRONMENT — location, time
    "layer_11": "mood",        # ATMOSPHERE — mood, lighting
    # Legacy groups
    "expression": "expression",
    "pose": "action",
    "camera": "camera",
    "location_indoor": "environment",
    "location_outdoor": "environment",
    "lighting": "mood",
    "mood": "mood",
    "time": "environment",
}
