"""Creative Lab -> Studio bridge -- session creation & send-to-studio."""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, NARRATOR_NEGATIVE_PROMPT_EXTRA
from models.creative import CreativeSession
from models.scene import Scene
from models.storyboard import Storyboard
from models.storyboard_character import StoryboardCharacter
from services.creative_utils import parse_image_prompt_to_tags
from services.image_generation_core import compose_scene_with_style, resolve_style_loras_from_group

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
    characters: dict[str, dict],
    fallback_char_id: int | None,
    style_loras: list[dict] | None = None,
    db: Session | None = None,
) -> Scene:
    """Build a single Scene from pipeline output dict.

    When db is provided (deep_parse=True), applies full composition
    via compose_scene_with_style (same logic as Studio Direct):
      StyleProfile (quality/embeddings) → V3 composition.
    """
    image_prompt = s.get("image_prompt", "")
    context_tags = s.get("context_tags")
    negative_prompt = DEFAULT_SCENE_NEGATIVE_PROMPT

    if db and image_prompt:
        tags = parse_image_prompt_to_tags(image_prompt)
        speaker = s.get("speaker", "A")
        char_id = characters.get(speaker, {}).get("id") or fallback_char_id

        image_prompt, negative_prompt, _warnings = compose_scene_with_style(
            raw_prompt=", ".join(tags),
            negative_prompt=negative_prompt,
            character_id=char_id,
            storyboard_id=storyboard_id,
            style_loras=style_loras or [],
            db=db,
        )

        # Narrator scenes: append person-exclusion tags
        is_narrator = "no_humans" in image_prompt.lower().replace(" ", "_")
        if is_narrator:
            negative_prompt = f"{negative_prompt}, {NARRATOR_NEGATIVE_PROMPT_EXTRA}"

        context_tags = {"original_tags": tags, "composed": True}

    return Scene(
        storyboard_id=storyboard_id,
        order=s.get("order", 0),
        script=s.get("script", ""),
        speaker=s.get("speaker", "A"),
        duration=s.get("duration", 2.5),
        image_prompt=image_prompt,
        image_prompt_ko=s.get("image_prompt_ko", ""),
        negative_prompt=negative_prompt,
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

    # 1. Create storyboard (transfer duration/language from session context)
    storyboard = Storyboard(
        group_id=group_id,
        title=resolved_title,
        structure=structure,
        description=session.objective,
        duration=ctx.get("duration"),
        language=ctx.get("language"),
    )
    db.add(storyboard)
    db.flush()

    # 2. Resolve style LoRAs for composition
    style_loras: list[dict] = []
    if deep_parse:
        style_loras = resolve_style_loras_from_group(group_id, db)

    # 3. Link characters
    characters = ctx.get("characters") or {}
    if characters:
        _link_characters(db, storyboard.id, characters)
    elif session.character_id:
        # Monologue fallback: single character_id → speaker "A"
        db.add(
            StoryboardCharacter(
                storyboard_id=storyboard.id,
                speaker="A",
                character_id=session.character_id,
            )
        )

    # 4. Create scenes (db=session enables compose_scene_with_style for deep_parse)
    for s in scenes_data:
        scene = _build_scene(
            s,
            storyboard.id,
            characters,
            session.character_id,
            style_loras=style_loras,
            db=db if deep_parse else None,
        )
        db.add(scene)

    db.commit()
    return {"storyboard_id": storyboard.id, "scene_count": len(scenes_data)}
