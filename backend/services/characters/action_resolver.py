"""Auto-populate scene_character_actions from Gemini context_tags."""

from sqlalchemy.orm import Session

from config import logger
from models.tag import Tag

# Tag 2단계 계층: category(대분류 4종) + group_name(소분류 24종).
# context_tags 키 중 character_actions에 해당하는 group_name 집합.
_ACTION_GROUPS = frozenset({"expression", "gaze", "pose", "action"})


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
        for cat in _ACTION_GROUPS:
            value = context_tags.get(cat)
            if not value:
                continue
            # gaze is a single string; others are lists
            tags = [value] if isinstance(value, str) else value
            all_tag_names.update(t.strip() for t in tags if t.strip())

    if not all_tag_names:
        return scenes

    # Batch query: resolve (tag_name, group_name) -> (tag_id, default_layer)
    tag_rows = (
        db.query(Tag.id, Tag.name, Tag.group_name, Tag.default_layer)
        .filter(Tag.name.in_(all_tag_names), Tag.group_name.in_(_ACTION_GROUPS))
        .all()
    )
    tag_lookup: dict[tuple[str, str], tuple[int, int]] = {
        (row.name, row.group_name): (row.id, row.default_layer) for row in tag_rows
    }

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

        is_multi = scene.get("scene_mode") == "multi"
        speaker = scene.get("speaker", "")
        char_id = speaker_map.get(speaker)
        if not char_id and not is_multi:
            continue  # Narrator or unknown speaker (single scene)

        context_tags = scene.get("context_tags") or {}

        # Determine which characters get actions
        if is_multi:
            target_char_ids = [cid for cid in (character_id, character_b_id) if cid]
        else:
            target_char_ids = [char_id] if char_id else []

        actions: list[dict] = []
        for cid in target_char_ids:
            for cat in _ACTION_GROUPS:
                value = context_tags.get(cat)
                if not value:
                    continue
                tags = [value] if isinstance(value, str) else value
                for tag_name in tags:
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue
                    result = tag_lookup.get((tag_name, cat))
                    if not result:
                        continue
                    tag_id, _ = result
                    actions.append(
                        {
                            "character_id": cid,
                            "tag_id": tag_id,
                            "weight": 1.0,
                        }
                    )

        if actions:
            scene["character_actions"] = actions
            logger.debug(
                "[CharacterActionResolver] Scene %s: %d actions for %d character(s)",
                scene.get("scene_id", "?"),
                len(actions),
                len(target_char_ids),
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
    for cat in _ACTION_GROUPS:
        value = context_tags.get(cat)
        if not value:
            continue
        tags = [value] if isinstance(value, str) else value
        tag_names.update(t.strip() for t in tags if t.strip())

    if not tag_names:
        return None

    rows = (
        db.query(Tag.id, Tag.name, Tag.group_name)
        .filter(Tag.name.in_(tag_names), Tag.group_name.in_(_ACTION_GROUPS))
        .all()
    )
    tag_lookup: dict[tuple[str, str], int] = {(r.name, r.group_name): r.id for r in rows}

    actions: list[dict] = []
    for cat in _ACTION_GROUPS:
        value = context_tags.get(cat)
        if not value:
            continue
        tags = [value] if isinstance(value, str) else value
        for name in tags:
            name = name.strip()
            tid = tag_lookup.get((name, cat))
            if tid:
                actions.append({"character_id": character_id, "tag_id": tid, "weight": 1.0})

    return actions if actions else None
