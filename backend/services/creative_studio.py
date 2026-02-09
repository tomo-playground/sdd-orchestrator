"""Creative Lab -> Studio bridge -- session creation & send-to-studio."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.creative import CreativeSession
from models.scene import Scene
from models.storyboard import Storyboard
from models.storyboard_character import StoryboardCharacter
from services.creative_utils import parse_image_prompt_to_tags

# ── Shorts Session Creation ─────────────────────────────────


def resolve_characters(
    db: Session,
    character_ids: dict[str, int] | None,
) -> dict[str, dict]:
    """Build speaker->character mapping from character_ids request field."""
    if not character_ids:
        return {}

    from models.character import Character

    characters: dict[str, dict] = {}
    for speaker, char_id in character_ids.items():
        char = db.get(Character, char_id)
        if char and not char.deleted_at:
            tag_names = [ct.tag.name for ct in (char.tags or []) if ct.tag]
            characters[speaker] = {
                "id": char_id,
                "name": char.name,
                "tags": tag_names,
            }
    return characters


def create_shorts_session(
    db: Session,
    *,
    topic: str,
    duration: int,
    structure: str,
    language: str,
    character_id: int | None,
    character_ids: dict[str, int] | None,
    references: list[str] | None,
    max_rounds: int,
    director_mode: str | None,
) -> CreativeSession:
    """Create a V2 shorts pipeline session with character resolution."""
    from services.creative_tasks import get_default_criteria

    try:
        criteria = get_default_criteria("scenario")
    except (ValueError, ModuleNotFoundError):
        criteria = {}

    characters = resolve_characters(db, character_ids)
    primary_char_id = character_id or (list(character_ids.values())[0] if character_ids else None)

    # Legacy single character: resolve tags for cinematographer
    character_tags: list[str] | None = None
    character_name: str | None = None
    if characters:
        character_name = characters.get("A", {}).get("name")
    elif primary_char_id:
        from models.character import Character

        char = db.get(Character, primary_char_id)
        if char and not char.deleted_at:
            character_name = char.name
            character_tags = [ct.tag.name for ct in (char.tags or []) if ct.tag]

    session = CreativeSession(
        objective=topic,
        evaluation_criteria=criteria,
        character_id=primary_char_id,
        context={
            "duration": duration,
            "structure": structure,
            "language": language,
            "references": references or [],
            "characters": characters if characters else None,
            "character_name": character_name,
            "character_tags": character_tags,
        },
        max_rounds=max_rounds,
        status="created",
        session_type="shorts",
        director_mode=director_mode,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ── Send to Studio ──────────────────────────────────────────


def _link_characters(
    db: Session,
    storyboard_id: int,
    characters: dict[str, dict],
) -> None:
    """Create StoryboardCharacter records for each speaker mapping."""
    for speaker, info in characters.items():
        sc = StoryboardCharacter(
            storyboard_id=storyboard_id,
            speaker=speaker,
            character_id=info["id"],
        )
        db.add(sc)


def _build_scene(
    s: dict,
    storyboard_id: int,
    builder,
    characters: dict[str, dict],
    fallback_char_id: int | None,
) -> Scene:
    """Build a single Scene from pipeline output dict."""
    image_prompt = s.get("image_prompt", "")
    context_tags = s.get("context_tags")

    if builder and image_prompt:
        tags = parse_image_prompt_to_tags(image_prompt)
        speaker = s.get("speaker", "A")
        char_id = characters.get(speaker, {}).get("id") or fallback_char_id
        if char_id:
            image_prompt = builder.compose_for_character(char_id, tags)
        else:
            image_prompt = builder.compose(tags)
        context_tags = {"original_tags": tags, "composed": True}

    return Scene(
        storyboard_id=storyboard_id,
        order=s.get("order", 0),
        script=s.get("script", ""),
        speaker=s.get("speaker", "A"),
        duration=s.get("duration", 2.5),
        image_prompt=image_prompt,
        image_prompt_ko=s.get("image_prompt_ko", ""),
        context_tags=context_tags,
    )


def send_to_studio(
    db: Session,
    session: CreativeSession,
    group_id: int,
    title: str | None = None,
    deep_parse: bool = False,
) -> dict:
    """Create a Storyboard + Scenes from a completed creative session.

    Returns:
        {"storyboard_id": int, "scene_count": int}

    Raises:
        ValueError: if session has no scenes in final_output.
    """
    final = session.final_output or {}
    scenes_data = final.get("scenes", [])
    if not scenes_data:
        raise ValueError("No scenes to send")

    ctx = dict(session.context or {})
    resolved_title = title or f"Creative Lab: {session.objective[:50]}"
    structure = ctx.get("structure", "Monologue")

    # 1. Create storyboard
    storyboard = Storyboard(
        group_id=group_id,
        title=resolved_title,
        structure=structure,
        description=session.objective,
    )
    db.add(storyboard)
    db.flush()

    # 2. Optionally build prompt composer
    builder = None
    if deep_parse:
        from services.prompt.v3_composition import V3PromptBuilder

        builder = V3PromptBuilder(db)

    # 3. Link characters
    characters = ctx.get("characters", {})
    if characters:
        _link_characters(db, storyboard.id, characters)

    # 4. Create scenes
    for s in scenes_data:
        scene = _build_scene(
            s,
            storyboard.id,
            builder,
            characters,
            session.character_id,
        )
        db.add(scene)

    db.commit()
    return {"storyboard_id": storyboard.id, "scene_count": len(scenes_data)}
