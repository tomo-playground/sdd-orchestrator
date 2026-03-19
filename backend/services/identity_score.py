"""Identity score calculation for character visual consistency.

Computes how well a generated image matches the character's identity traits
(hair color, eye color, hair style, etc.) based on WD14 tag detection.
"""

from __future__ import annotations

from config import IDENTITY_SCORE_GROUPS, WD14_THRESHOLD, logger
from services.keywords import normalize_prompt_token


def extract_character_identity_tags(character_tags: list[dict]) -> list[str]:
    """Extract identity-relevant tags from character tag list.

    Args:
        character_tags: List of dicts with at least "name" and "group_name" keys.
            Typically from CharacterTag → Tag join.

    Returns:
        Normalized tag names belonging to IDENTITY_SCORE_GROUPS.
    """
    result: list[str] = []
    for t in character_tags:
        group = t.get("group_name") or ""
        if group in IDENTITY_SCORE_GROUPS:
            name = normalize_prompt_token(t.get("name", ""))
            if name:
                result.append(name)
    return result


def compute_identity_score(
    identity_tags: list[str],
    wd14_tags: list[dict],
    threshold: float = WD14_THRESHOLD,
) -> float:
    """Compute identity consistency score.

    Args:
        identity_tags: Normalized character identity tags.
        wd14_tags: WD14 detection results (list of {"tag", "score", ...}).
        threshold: Minimum WD14 confidence to consider a tag detected.

    Returns:
        0.0–1.0 ratio of identity tags detected by WD14.
        Returns 1.0 if identity_tags is empty (no constraint).
    """
    if not identity_tags:
        return 1.0

    detected_set = {normalize_prompt_token(item["tag"]) for item in wd14_tags if item["score"] >= threshold}

    matched = sum(1 for tag in identity_tags if tag in detected_set)
    return matched / len(identity_tags)


def extract_identity_signature(
    wd14_tags: list[dict],
    db,
    threshold: float = WD14_THRESHOLD,
) -> dict[str, list[str]]:
    """Extract identity group-level signature from WD14 results.

    Queries Tag DB to resolve group_name for each detected tag,
    then groups by IDENTITY_SCORE_GROUPS.

    Returns:
        {"hair_color": ["black_hair"], "eye_color": ["blue_eyes"], ...}
        Groups with no detected tags have empty lists.
    """
    from models.tag import Tag

    detected_names = [normalize_prompt_token(item["tag"]) for item in wd14_tags if item["score"] >= threshold]
    detected_names = [n for n in detected_names if n]

    if not detected_names:
        return {group: [] for group in IDENTITY_SCORE_GROUPS}

    rows = (
        db.query(Tag.name, Tag.group_name)
        .filter(Tag.name.in_(detected_names), Tag.group_name.in_(IDENTITY_SCORE_GROUPS))
        .all()
    )

    signature: dict[str, list[str]] = {group: [] for group in IDENTITY_SCORE_GROUPS}
    for row in rows:
        signature[row.group_name].append(row.name)
    return signature


def load_character_identity_tags(character_id: int, db) -> list[str]:
    """Load character tags from DB and extract identity-relevant ones.

    Args:
        character_id: Character primary key.
        db: SQLAlchemy Session.

    Returns:
        List of normalized identity tag names, empty if character not found.
    """
    from models.associations import CharacterTag
    from models.tag import Tag

    try:
        rows = (
            db.query(Tag.name, Tag.group_name)
            .join(CharacterTag, CharacterTag.tag_id == Tag.id)
            .filter(CharacterTag.character_id == character_id)
            .all()
        )
        tag_dicts = [{"name": r.name, "group_name": r.group_name} for r in rows]
        return extract_character_identity_tags(tag_dicts)
    except Exception as exc:
        logger.warning("Failed to load identity tags for character %d: %s", character_id, exc)
        return []
