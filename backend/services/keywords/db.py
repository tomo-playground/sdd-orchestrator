from __future__ import annotations

from typing import Any

from database import SessionLocal
from models.tag import Synonym, Tag, TagEffectiveness

from .core import IGNORE_TOKENS, normalize_prompt_token


def load_tags_from_db() -> dict[str, list[str]]:
    """Load tags from database grouped by group_name."""
    db = SessionLocal()
    try:
        tags = db.query(Tag).order_by(Tag.group_name, Tag.name).all()
        grouped: dict[str, list[str]] = {}
        for tag in tags:
            group = tag.group_name or "other"
            if group not in grouped:
                grouped[group] = []
            grouped[group].append(tag.name)
        return grouped
    finally:
        db.close()


def load_synonyms_from_db() -> dict[str, str]:
    """Load synonym mappings from database. Returns {synonym: tag_name}."""
    db = SessionLocal()
    try:
        synonyms = db.query(Synonym).join(Tag).all()
        return {
            normalize_prompt_token(s.synonym): normalize_prompt_token(s.tag.name)
            for s in synonyms if s.tag
        }
    finally:
        db.close()


def load_allowed_tags_from_db() -> set[str]:
    """Load all tag names from database as allowed set."""
    grouped = load_tags_from_db()
    allowed: set[str] = set()
    for tags in grouped.values():
        for tag in tags:
            allowed.add(normalize_prompt_token(tag))
    return allowed


def load_known_keywords() -> set[str]:
    """Load all known keywords from database."""
    allowed = load_allowed_tags_from_db()
    synonyms = load_synonyms_from_db()
    known = allowed.copy()
    known.update(synonyms.keys())
    known.update(IGNORE_TOKENS)
    return known


def load_tag_effectiveness_map() -> dict[str, tuple[float | None, int]]:
    """Load effectiveness scores for all tags. Returns {tag_name: (effectiveness, use_count)}."""
    db = SessionLocal()
    try:
        results = (
            db.query(Tag.name, TagEffectiveness.effectiveness, TagEffectiveness.use_count)
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .all()
        )
        return {
            normalize_prompt_token(name): (eff, use_count or 0)
            for name, eff, use_count in results
        }
    finally:
        db.close()


def update_tag_effectiveness(
    prompt_tags: list[str],
    detected_tags: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update tag effectiveness based on WD14 detection results."""
    from .core import logger

    if not prompt_tags:
        return {"updated": [], "new": [], "stats": {}}

    normalized_prompt = {normalize_prompt_token(t) for t in prompt_tags if t}
    normalized_prompt.discard("")

    detected_lookup: dict[str, float] = {}
    for item in detected_tags:
        tag_name = item.get("tag", "")
        confidence = float(item.get("confidence", 0.0))
        normalized = normalize_prompt_token(tag_name)
        if normalized:
            if normalized not in detected_lookup or confidence > detected_lookup[normalized]:
                detected_lookup[normalized] = confidence

    db = SessionLocal()
    try:
        updated = []
        new_records = []

        for tag_name in normalized_prompt:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                continue

            eff = db.query(TagEffectiveness).filter(TagEffectiveness.tag_id == tag.id).first()
            if not eff:
                eff = TagEffectiveness(tag_id=tag.id, use_count=0, match_count=0, total_confidence=0.0)
                db.add(eff)
                new_records.append(tag_name)

            eff.use_count += 1
            if tag_name in detected_lookup:
                eff.match_count += 1
                eff.total_confidence += detected_lookup[tag_name]

            if eff.use_count > 0:
                eff.effectiveness = eff.match_count / eff.use_count

            updated.append({
                "tag": tag_name,
                "use_count": eff.use_count,
                "match_count": eff.match_count,
                "effectiveness": round(eff.effectiveness, 3),
                "detected": tag_name in detected_lookup,
            })

        db.commit()
        return {
            "updated": updated,
            "new": new_records,
            "stats": {
                "prompt_tags": len(normalized_prompt),
                "detected_tags": len(detected_lookup),
                "records_updated": len(updated),
            },
        }
    except Exception as e:
        db.rollback()
        logger.exception("Failed to update tag effectiveness")
        return {"error": str(e), "updated": [], "new": [], "stats": {}}
    finally:
        db.close()


def get_effective_tags(min_effectiveness: float = 0.5, min_uses: int = 5) -> dict[str, list[str]]:
    """Get tags grouped by effectiveness level."""
    db = SessionLocal()
    try:
        results = (
            db.query(Tag.name, Tag.group_name, TagEffectiveness.effectiveness, TagEffectiveness.use_count)
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(Tag.group_name.in_([
                "expression", "gaze", "pose", "action", "camera",
                "environment", "location_indoor", "location_outdoor",
                "background_type", "time_weather", "lighting", "mood"
            ]))
            .all()
        )
        high, medium, low, unknown = [], [], [], []
        for name, _group, effectiveness, use_count in results:
            if effectiveness is None or (use_count or 0) < min_uses:
                unknown.append(name)
            elif effectiveness >= 0.7:
                high.append(name)
            elif effectiveness >= 0.4:
                medium.append(name)
            else:
                low.append(name)
        return {"high": high, "medium": medium, "low": low, "unknown": unknown}
    finally:
        db.close()


def get_tag_effectiveness_report() -> list[dict[str, Any]]:
    """Get full effectiveness report for all scene-related tags."""
    db = SessionLocal()
    try:
        results = (
            db.query(
                Tag.name, Tag.group_name,
                TagEffectiveness.use_count, TagEffectiveness.match_count, TagEffectiveness.effectiveness,
            )
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(Tag.group_name.in_([
                "expression", "gaze", "pose", "action", "camera",
                "environment", "location_indoor", "location_outdoor",
                "background_type", "time_weather", "lighting", "mood", "style"
            ]))
            .order_by(TagEffectiveness.effectiveness.desc().nullslast(), Tag.name)
            .all()
        )
        return [
            {
                "tag": name, "group": group, "use_count": use_count or 0,
                "match_count": match_count or 0,
                "effectiveness": round(effectiveness, 3) if effectiveness else None,
            }
            for name, group, use_count, match_count, effectiveness in results
        ]
    finally:
        db.close()


# Mapping from DB group_name to Gemini-friendly category names
_DB_GROUP_TO_GEMINI_CATEGORY = {
    # Scene expression groups
    "subject": "person/subject",
    "expression": "expression",
    "gaze": "gaze",
    "pose": "pose",
    "action": "action",
    "camera": "shot_type/camera_angle",
    # Environment
    "environment": "location",
    "location_indoor": "indoor_location",
    "location_outdoor": "outdoor_location",
    "background_type": "background",
    "time_weather": "time/weather",
    "lighting": "lighting",
    # Others
    "mood": "mood",
    "style": "style",
    "quality": "quality",
    # Identity groups (for character, not for scene generation)
    "hair_color": None, "hair_length": None, "hair_style": None, "hair_accessory": None,
    "eye_color": None, "skin_color": None, "body_feature": None, "appearance": None,
    "identity": None, "clothing": None,
}

# Groups to include in Gemini keyword context (scene-related only)
_SCENE_GROUPS = [
    "subject", "expression", "gaze", "pose", "action", "camera",
    "environment", "location_indoor", "location_outdoor", "background_type",
    "time_weather", "lighting", "mood", "style", "quality"
]
