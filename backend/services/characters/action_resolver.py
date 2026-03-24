"""Auto-populate scene_character_actions from Gemini context_tags."""

from sqlalchemy.orm import Session

from config import SPEAKER_A, SPEAKER_B, logger
from models.tag import Tag

# Tag 2단계 계층: category(대분류 4종) + group_name(소분류 37종).
# Gemini context_tags의 키 (인터페이스 계약 — 변경하지 않는다).
_CONTEXT_TAG_KEYS = frozenset({"expression", "gaze", "pose", "action"})
# DB group_name 필터용 (세분화된 그룹).
_ACTION_DB_GROUPS = frozenset(
    {
        "expression",
        "gaze",
        "pose",
        "action_body",
        "action_hand",
        "action_daily",
    }
)


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
        speaker_map[SPEAKER_A] = character_id
    if character_b_id:
        speaker_map[SPEAKER_B] = character_b_id

    if not speaker_map:
        return scenes

    # Collect all tag names across scenes for batch DB lookup
    all_tag_names: set[str] = set()
    for scene in scenes:
        context_tags = scene.get("context_tags") or {}
        for cat in _CONTEXT_TAG_KEYS:
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
        .filter(Tag.name.in_(all_tag_names), Tag.group_name.in_(_ACTION_DB_GROUPS))
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

        # 단일 캐릭터 + speaker 빈 문자열 폴백: character_id가 있고 B가 없으면 SPEAKER_A로 간주
        if not speaker and character_id and not character_b_id:
            speaker = SPEAKER_A

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
            for cat in _CONTEXT_TAG_KEYS:
                value = context_tags.get(cat)
                if not value:
                    continue
                tags = [value] if isinstance(value, str) else value
                for tag_name in tags:
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue
                    # Try exact (tag, context_key) first
                    result = tag_lookup.get((tag_name, cat))
                    if not result and cat == "action":
                        # context_tags key "action" → DB groups action_body/hand/daily
                        for db_group in ("action_body", "action_hand", "action_daily"):
                            result = tag_lookup.get((tag_name, db_group))
                            if result:
                                break
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
    for cat in _CONTEXT_TAG_KEYS:
        value = context_tags.get(cat)
        if not value:
            continue
        tags = [value] if isinstance(value, str) else value
        tag_names.update(t.strip() for t in tags if t.strip())

    if not tag_names:
        return None

    rows = (
        db.query(Tag.id, Tag.name, Tag.group_name)
        .filter(Tag.name.in_(tag_names), Tag.group_name.in_(_ACTION_DB_GROUPS))
        .all()
    )
    tag_lookup: dict[tuple[str, str], int] = {(r.name, r.group_name): r.id for r in rows}

    actions: list[dict] = []
    for cat in _CONTEXT_TAG_KEYS:
        value = context_tags.get(cat)
        if not value:
            continue
        tags = [value] if isinstance(value, str) else value
        for name in tags:
            name = name.strip()
            # Try exact (tag, context_key) first
            tid = tag_lookup.get((name, cat))
            if not tid and cat == "action":
                # context_tags key "action" → DB groups action_body/hand/daily
                for db_group in ("action_body", "action_hand", "action_daily"):
                    tid = tag_lookup.get((name, db_group))
                    if tid:
                        break
            if tid:
                actions.append({"character_id": character_id, "tag_id": tid, "weight": 1.0})

    return actions if actions else None
