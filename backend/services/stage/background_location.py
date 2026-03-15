"""Stage Workflow — Location extraction & background quality helpers.

Provides utilities for grouping scenes by location tags, resolving
aliases, computing stable location keys, and background quality overrides.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import logger
from models.scene import Scene
from models.tag import Tag
from services.keywords.db_cache import TagAliasCache

# ── Background quality overrides ─────────────────────────────────────
# StyleProfile.default_positive is optimized for character scene quality.
# Background generation uses different quality tags (atmospheric, no face focus).
# Keyed by StyleProfile ID.
_BG_QUALITY_OVERRIDES: dict[int, str] = {
    2: "RAW photo, soft ambient lighting, muted tones, shallow depth of field, natural light, 35mm film, high quality",  # Realistic
}


def resolve_bg_quality_tags(style_ctx) -> list[str] | None:
    """Resolve background-specific quality tags.

    Uses _BG_QUALITY_OVERRIDES when available, falls back to StyleProfile.default_positive.
    """
    if not style_ctx:
        return None
    override = _BG_QUALITY_OVERRIDES.get(style_ctx.profile_id)
    quality_str = override if override is not None else style_ctx.default_positive
    return quality_str.split(", ") if quality_str else None


# ── Location extraction ──────────────────────────────────────────────

_LOCATION_GROUP_PREFIX = "location_"


def find_best_matching_bg(scene_key: str, loc_to_bg: dict[str, dict]) -> tuple[dict | None, str]:
    """Find the best matching BG when exact key doesn't match (subset/overlap)."""
    scene_set = set(scene_key.split("_"))
    best_info, best_key, best_score = None, scene_key, 0.0
    for bg_key, bg_info in loc_to_bg.items():
        bg_set = set(bg_key.split("_"))
        overlap = len(scene_set & bg_set) / len(scene_set | bg_set)
        if (scene_set <= bg_set or bg_set <= scene_set or overlap > 0.85) and overlap > best_score:
            best_info, best_key, best_score = bg_info, bg_key, overlap
    return best_info, best_key


def _filter_location_tags(env_tags: list[str], db: Session) -> list[str]:
    """Filter environment tags to location-only (group_name starts with 'location_') or background_type."""
    if not env_tags:
        return []
    normed = [t.lower().strip() for t in env_tags]
    rows = (
        db.query(Tag.name)
        .filter(
            Tag.name.in_(normed),
            (Tag.group_name.like(f"{_LOCATION_GROUP_PREFIX}%")) | (Tag.group_name == "background_type"),
        )
        .all()
    )
    return [r.name for r in rows]


def _resolve_location_aliases(tags: list[str]) -> list[str]:
    """Apply tag alias resolution for location grouping (e.g. coffee_shop → cafe)."""
    resolved = []
    for tag in tags:
        replacement = TagAliasCache.get_replacement(tag)
        resolved.append(replacement if isinstance(replacement, str) else tag)
    return resolved


def compute_location_key(env_tags: list[str], db: Session) -> str:
    """Compute a stable location key from environment tags.

    Used by both extract_locations_from_scenes and assign_backgrounds_to_scenes
    to ensure consistent grouping.
    """
    loc_tags = _filter_location_tags(env_tags, db)
    if not loc_tags:
        loc_tags = env_tags[:1]
    loc_tags = _resolve_location_aliases(loc_tags)
    return "_".join(sorted(set(loc_tags)))


def _merge_subset_locations(loc_map: dict[str, dict]) -> dict[str, dict]:
    """Merge locations whose key tags are a subset of a larger location."""
    if len(loc_map) <= 1:
        return loc_map

    keys = sorted(loc_map.keys(), key=lambda k: len(loc_map[k]["scene_ids"]), reverse=True)
    merged: dict[str, dict] = {}
    absorbed: set[str] = set()

    for key in keys:
        if key in absorbed:
            continue
        key_set = set(key.split("_"))
        merged[key] = loc_map[key]
        for other in keys:
            if other == key or other in absorbed:
                continue
            other_set = set(other.split("_"))
            overlap = len(key_set & other_set) / len(key_set | other_set)
            if key_set <= other_set or other_set <= key_set or overlap > 0.85:
                merged[key]["scene_ids"].extend(loc_map[other]["scene_ids"])
                for t in loc_map[other]["tags"]:
                    if t not in merged[key]["tags"]:
                        merged[key]["tags"].append(t)
                absorbed.add(other)
                logger.info("[Stage] Merged location '%s' into '%s' (overlap=%.2f)", other, key, overlap)

    return merged


def extract_locations_from_scenes(scenes: list[Scene], db: Session) -> dict[str, dict]:
    """Group scenes by location tags (excluding props) to derive locations.

    Uses Tag.group_name 'location_*' filter + alias resolution for accurate grouping.
    Returns: {location_key: {"name": str, "tags": list[str], "scene_ids": list[int]}}
    """
    TagAliasCache.initialize(db)
    loc_map: dict[str, dict] = {}

    for scene in scenes:
        env_tags = (scene.context_tags or {}).get("environment", [])
        if not env_tags:
            continue
        key = compute_location_key(env_tags, db)
        if key not in loc_map:
            loc_map[key] = {
                "name": key.split("_")[0].replace("_", " ").title(),
                "tags": list(env_tags),  # keep ALL tags for image generation
                "scene_ids": [],
            }
        else:
            # Merge env_tags: union of all tags across scenes in same location
            existing = set(loc_map[key]["tags"])
            for t in env_tags:
                if t not in existing:
                    loc_map[key]["tags"].append(t)
                    existing.add(t)
        loc_map[key]["scene_ids"].append(scene.id)

    return _merge_subset_locations(loc_map)
