"""Auto-populate scene_character_actions from Gemini context_tags."""

from sqlalchemy.orm import Session

from config import logger
from models.tag import Tag

# context_tags categories that map to character actions
_ACTION_CATEGORIES = frozenset({"expression", "gaze", "pose", "action"})


def auto_populate_character_actions(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None,
    db: Session,
) -> list[dict]:
    """Convert context_tags into character_actions for each scene.

    Extracts expression/gaze/pose/action tags from context_tags,
    maps speaker to character_id, and resolves tag_ids via batch DB query.

    Args:
        scenes: List of scene dicts from Gemini response.
        character_id: Speaker A character ID.
        character_b_id: Speaker B character ID.
        db: SQLAlchemy session.

    Returns:
        The same scenes list with character_actions populated.
    """
    # Build speaker -> character_id mapping
    speaker_map: dict[str, int] = {}
    if character_id:
        speaker_map["A"] = character_id
    if character_b_id:
        speaker_map["B"] = character_b_id

    if not speaker_map:
        return scenes

    # Collect all tag names across scenes for batch DB lookup
    all_tag_names: set[str] = set()
    for scene in scenes:
        context_tags = scene.get("context_tags") or {}
        for cat in _ACTION_CATEGORIES:
            value = context_tags.get(cat)
            if not value:
                continue
            # gaze is a single string; others are lists
            tags = [value] if isinstance(value, str) else value
            all_tag_names.update(t.strip() for t in tags if t.strip())

    if not all_tag_names:
        return scenes

    # Batch query: resolve tag_name -> (tag_id, default_layer)
    tag_rows = db.query(Tag.id, Tag.name, Tag.default_layer).filter(Tag.name.in_(all_tag_names)).all()
    tag_lookup: dict[str, tuple[int, int]] = {row.name: (row.id, row.default_layer) for row in tag_rows}

    logger.info(
        "[CharacterActionResolver] Resolved %d/%d tags from DB",
        len(tag_lookup),
        len(all_tag_names),
    )

    # Populate character_actions per scene
    for scene in scenes:
        # Skip if character_actions already exist
        if scene.get("character_actions"):
            continue

        speaker = scene.get("speaker", "")
        char_id = speaker_map.get(speaker)
        if not char_id:
            continue  # Narrator or unknown speaker

        context_tags = scene.get("context_tags") or {}
        actions: list[dict] = []

        for cat in _ACTION_CATEGORIES:
            value = context_tags.get(cat)
            if not value:
                continue
            tags = [value] if isinstance(value, str) else value
            for tag_name in tags:
                tag_name = tag_name.strip()
                if not tag_name or tag_name not in tag_lookup:
                    continue
                tag_id, _ = tag_lookup[tag_name]
                actions.append(
                    {
                        "character_id": char_id,
                        "tag_id": tag_id,
                        "weight": 1.0,
                    }
                )

        if actions:
            scene["character_actions"] = actions
            logger.debug(
                "[CharacterActionResolver] Scene %s: %d actions for character %d",
                scene.get("scene_id", "?"),
                len(actions),
                char_id,
            )

    return scenes


def extract_actions_from_context_tags(
    context_tags: dict | None,
    character_id: int,
    db: Session,
) -> list[dict] | None:
    """Extract character_actions from a single scene's context_tags.

    Used by creative_studio._build_scene where scenes don't have DB IDs yet.
    Returns list of action dicts or None if no matching tags found.
    """
    if not context_tags or not character_id:
        return None

    tag_names: set[str] = set()
    for cat in _ACTION_CATEGORIES:
        value = context_tags.get(cat)
        if not value:
            continue
        tags = [value] if isinstance(value, str) else value
        tag_names.update(t.strip() for t in tags if t.strip())

    if not tag_names:
        return None

    rows = db.query(Tag.id, Tag.name).filter(Tag.name.in_(tag_names)).all()
    tag_lookup = {r.name: r.id for r in rows}

    actions: list[dict] = []
    for cat in _ACTION_CATEGORIES:
        value = context_tags.get(cat)
        if not value:
            continue
        tags = [value] if isinstance(value, str) else value
        for name in tags:
            name = name.strip()
            tid = tag_lookup.get(name)
            if tid:
                actions.append({"character_id": character_id, "tag_id": tid, "weight": 1.0})

    return actions if actions else None
