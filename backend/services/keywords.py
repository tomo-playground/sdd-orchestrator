"""Keyword management service.

Handles keyword normalization, synonyms, categories, and suggestions.
All keyword data is sourced from PostgreSQL database (tags, synonyms tables).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

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
# These are typically low-quality or unwanted tags
IGNORE_TOKENS = frozenset([
    "nsfw", "nude", "uncensored", "cleavage", "text", "watermark",
    "signature", "logo", "username", "artist name", "copyright",
    "low quality", "worst quality", "normal quality", "bad quality",
    "bad anatomy", "bad hands", "missing fingers", "extra digits",
    "fewer digits", "extra limbs", "cloned face", "mutated",
    "deformed", "disfigured", "ugly", "blur", "blurry",
    "jpeg artifacts", "cropped", "out of frame", "highres", "absurdres",
])


def normalize_prompt_token(token: str) -> str:
    """Normalize a single prompt token for comparison."""
    cleaned = token.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return ""
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r":[0-9.]*$", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    return cleaned.strip().lower()


# --- DB-based keyword functions ---

# Mapping from DB group_name to Gemini-friendly category names
_DB_GROUP_TO_GEMINI_CATEGORY = {
    "subject": "person/subject",
    # Scene expression groups (세분화된 포즈/표정/시선/동작)
    "expression": "expression",
    "gaze": "gaze",
    "pose": "pose",
    "action": "action",
    "camera": "shot_type/camera_angle",
    "environment": "location/time/weather/lighting",
    "mood": "mood",
    "style": "style",
    "quality": "quality",
    # Identity groups (for character, not for scene generation)
    "hair_color": None,  # Skip - character identity
    "hair_length": None,
    "hair_style": None,
    "hair_accessory": None,
    "eye_color": None,
    "identity": None,
    "clothing": None,
}

# Groups to include in Gemini keyword context (scene-related only)
_SCENE_GROUPS = [
    "subject", "expression", "gaze", "pose", "action",
    "camera", "environment", "mood", "style", "quality"
]


def load_tags_from_db() -> dict[str, list[str]]:
    """Load tags from database grouped by group_name."""
    from database import SessionLocal
    from models.tag import Tag

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
    from database import SessionLocal
    from models.tag import Synonym, Tag

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


def expand_synonyms(tokens: list[str]) -> set[str]:
    """Expand a list of tokens to include all known synonyms."""
    synonym_lookup = load_synonyms_from_db()
    # Reverse lookup: tag -> synonyms
    reverse_map: dict[str, set[str]] = {}
    for syn, tag in synonym_lookup.items():
        if tag not in reverse_map:
            reverse_map[tag] = set()
        reverse_map[tag].add(syn)

    expanded: set[str] = set()
    for token in tokens:
        if not token:
            continue
        normalized = normalize_prompt_token(token)
        expanded.add(normalized)
        if normalized in reverse_map:
            expanded.update(reverse_map[normalized])
    return expanded


def load_tag_effectiveness_map() -> dict[str, tuple[float | None, int]]:
    """Load effectiveness scores for all tags. Returns {tag_name: (effectiveness, use_count)}."""
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

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


def format_keyword_context(filter_by_effectiveness: bool = True) -> str:
    """Format keyword categories for use in Gemini prompts (DB-based).

    Args:
        filter_by_effectiveness: If True, filters out low-effectiveness tags
            and prioritizes high-effectiveness tags.
    """
    grouped = load_tags_from_db()
    if not grouped:
        _get_logger().warning("No tags found in database")
        return ""

    # Load effectiveness data if filtering is enabled
    eff_map: dict[str, tuple[float | None, int]] = {}
    if filter_by_effectiveness:
        eff_map = load_tag_effectiveness_map()

    lines = ["Allowed Keywords (use exactly as written):"]
    for group in _SCENE_GROUPS:
        if group not in grouped:
            continue
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name is None:
            continue

        values = grouped[group]
        if not values:
            continue

        if filter_by_effectiveness and eff_map:
            # Filter and sort by effectiveness
            filtered_values = []
            for tag in values:
                normalized = normalize_prompt_token(tag)
                eff_data = eff_map.get(normalized)

                if eff_data is None:
                    # Unknown tag - include it (needs testing)
                    filtered_values.append((tag, 0.5, 0))  # default score
                else:
                    eff_score, use_count = eff_data
                    if eff_score is None:
                        # No effectiveness data yet - include it
                        filtered_values.append((tag, 0.5, use_count))
                    elif use_count < 3:
                        # Not enough data - include it
                        filtered_values.append((tag, 0.5, use_count))
                    elif eff_score < 0.3:
                        # Low effectiveness with sufficient data - skip
                        _get_logger().debug(f"Skipping low-effectiveness tag: {tag} ({eff_score:.2f})")
                        continue
                    else:
                        filtered_values.append((tag, eff_score, use_count))

            # Sort by effectiveness (high first), then alphabetically
            filtered_values.sort(key=lambda x: (-x[1], x[0]))
            values = [v[0] for v in filtered_values]

        if values:
            lines.append(f"- {category_name}: {', '.join(values)}")

    return "\n".join(lines)


def filter_prompt_tokens(prompt: str) -> str:
    """Filter prompt tokens to only include known/allowed keywords (DB-based)."""
    allowed = load_allowed_tags_from_db()
    synonym_lookup = load_synonyms_from_db()

    if not allowed:
        return _get_normalize_prompt_tokens()(prompt)

    tokens = _get_split_prompt_tokens()(prompt)
    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = normalize_prompt_token(token)
        if not normalized or normalized in IGNORE_TOKENS:
            continue
        base = None
        if normalized in allowed:
            base = normalized
        elif normalized in synonym_lookup and synonym_lookup[normalized] in allowed:
            base = synonym_lookup[normalized]
        if base and base not in seen:
            cleaned.append(base)
            seen.add(base)
    return ", ".join(cleaned)


# --- Keyword suggestions (still file-based for simplicity) ---

def update_keyword_suggestions(unknown_tags: list[str]) -> None:
    """Update the keyword suggestions cache with newly encountered unknown tags."""
    if not unknown_tags:
        return
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    try:
        if suggestions_path.exists():
            data = json.loads(suggestions_path.read_text(encoding="utf-8"))
        else:
            data = {}
        for tag in unknown_tags:
            data[tag] = int(data.get(tag, 0)) + 1
        suggestions_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        _get_logger().exception("Failed to update keyword suggestions")


def load_keyword_suggestions(min_count: int = 1, limit: int = 50) -> list[dict[str, Any]]:
    """Load keyword suggestions filtered by minimum count."""
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    if not suggestions_path.exists():
        return []
    try:
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
    except Exception:
        _get_logger().exception("Failed to read keyword suggestions")
        return []
    known = load_known_keywords()
    items = [
        {"tag": tag, "count": int(count)}
        for tag, count in data.items()
        if int(count) >= min_count and tag not in known
    ]
    items.sort(key=lambda item: (-item["count"], item["tag"]))
    return items[:max(1, limit)]


# --- Tag Effectiveness Feedback Loop ---

def update_tag_effectiveness(
    prompt_tags: list[str],
    detected_tags: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update tag effectiveness based on WD14 detection results.

    Args:
        prompt_tags: Tags used in the prompt (e.g., ["smile", "sitting", "library"])
        detected_tags: WD14 detection results (e.g., [{"tag": "smile", "confidence": 0.95}, ...])

    Returns:
        Summary of updates: {"updated": [...], "new": [...], "stats": {...}}
    """
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    if not prompt_tags:
        return {"updated": [], "new": [], "stats": {}}

    # Normalize prompt tags
    normalized_prompt = {normalize_prompt_token(t) for t in prompt_tags if t}
    normalized_prompt.discard("")

    # Build detected tag lookup: {normalized_name: confidence}
    detected_lookup: dict[str, float] = {}
    for item in detected_tags:
        tag_name = item.get("tag", "")
        confidence = float(item.get("confidence", 0.0))
        normalized = normalize_prompt_token(tag_name)
        if normalized:
            # Keep highest confidence if duplicate
            if normalized not in detected_lookup or confidence > detected_lookup[normalized]:
                detected_lookup[normalized] = confidence

    db = SessionLocal()
    try:
        updated = []
        new_records = []

        for tag_name in normalized_prompt:
            # Find tag in DB
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                # Try with underscore variant
                tag = db.query(Tag).filter(Tag.name == tag_name.replace(" ", "_")).first()
            if not tag:
                continue

            # Get or create effectiveness record
            eff = db.query(TagEffectiveness).filter(TagEffectiveness.tag_id == tag.id).first()
            if not eff:
                eff = TagEffectiveness(tag_id=tag.id, use_count=0, match_count=0, total_confidence=0.0)
                db.add(eff)
                new_records.append(tag_name)

            # Update counts
            eff.use_count += 1

            # Check if this tag was detected
            if tag_name in detected_lookup:
                eff.match_count += 1
                eff.total_confidence += detected_lookup[tag_name]

            # Recalculate effectiveness
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
        _get_logger().exception("Failed to update tag effectiveness")
        return {"error": str(e), "updated": [], "new": [], "stats": {}}
    finally:
        db.close()


def get_effective_tags(min_effectiveness: float = 0.5, min_uses: int = 5) -> dict[str, list[str]]:
    """Get tags grouped by effectiveness level.

    Args:
        min_effectiveness: Minimum effectiveness score to be considered "effective"
        min_uses: Minimum use count to be considered reliable data

    Returns:
        {"high": [...], "medium": [...], "low": [...], "unknown": [...]}
    """
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    db = SessionLocal()
    try:
        # Get all tags with effectiveness data
        results = (
            db.query(Tag.name, Tag.group_name, TagEffectiveness.effectiveness, TagEffectiveness.use_count)
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(Tag.group_name.in_(["expression", "gaze", "pose", "action", "camera", "environment", "mood"]))
            .all()
        )

        high = []  # effectiveness >= 0.7
        medium = []  # 0.4 <= effectiveness < 0.7
        low = []  # effectiveness < 0.4
        unknown = []  # no data or insufficient uses

        for name, group, effectiveness, use_count in results:
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
    from database import SessionLocal
    from models.tag import Tag, TagEffectiveness

    db = SessionLocal()
    try:
        results = (
            db.query(
                Tag.name,
                Tag.group_name,
                TagEffectiveness.use_count,
                TagEffectiveness.match_count,
                TagEffectiveness.effectiveness,
            )
            .outerjoin(TagEffectiveness, Tag.id == TagEffectiveness.tag_id)
            .filter(Tag.group_name.in_(["expression", "gaze", "pose", "action", "camera", "environment", "mood", "style"]))
            .order_by(TagEffectiveness.effectiveness.desc().nullslast(), Tag.name)
            .all()
        )

        return [
            {
                "tag": name,
                "group": group,
                "use_count": use_count or 0,
                "match_count": match_count or 0,
                "effectiveness": round(effectiveness, 3) if effectiveness else None,
            }
            for name, group, use_count, match_count, effectiveness in results
        ]
    finally:
        db.close()
