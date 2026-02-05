from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import UTC
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from models.associations import CharacterTag, SceneCharacterAction, SceneTag
from models.character import Character
from models.media_asset import MediaAsset
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import StoryboardRequest, StoryboardSave, StoryboardUpdate
from services.keywords import format_keyword_context
from services.presets import get_preset_by_structure


def strip_markdown_codeblock(text: str) -> str:
    """Strip markdown code block fences from Gemini response text.

    Handles variations: ```json, ```JSON, ``` with/without language tag,
    leading/trailing whitespace, and text outside the code block.
    """
    # Match ```<optional lang>\n<content>\n``` (case-insensitive, dotall)
    pattern = r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # No code block found -- return stripped original text
    return text.strip()


def normalize_scene_tags_key(scenes: list[dict]) -> list[dict]:
    """Rename 'scene_tags' to 'context_tags' if present in Gemini output."""
    for scene in scenes:
        if "scene_tags" in scene and "context_tags" not in scene:
            scene["context_tags"] = scene.pop("scene_tags")
    return scenes


def truncate_title(title: str, max_length: int = 190) -> str:
    """Truncate title if it exceeds constraints."""
    if not title:
        return "Untitled"
    if len(title) > max_length:
        return title[:max_length] + "..."
    return title


def serialize_scene(scene: Scene) -> dict:
    """Serialize a Scene ORM object to dict for API response."""
    return {
        "id": scene.id,
        "scene_id": scene.order,
        "script": scene.script,
        "speaker": scene.speaker,
        "duration": scene.duration,
        "description": scene.description,
        "image_prompt": scene.image_prompt,
        "image_prompt_ko": scene.image_prompt_ko,
        "negative_prompt": scene.negative_prompt,
        "image_url": scene.image_asset.url if scene.image_asset else scene.image_url,
        "width": scene.width,
        "height": scene.height,
        "context_tags": scene.context_tags,
        "tags": [{"tag_id": t.tag_id, "weight": t.weight} for t in scene.tags],
        "character_actions": [
            {"character_id": a.character_id, "tag_id": a.tag_id, "weight": a.weight} for a in scene.character_actions
        ],
        "use_reference_only": scene.use_reference_only,
        "reference_only_weight": scene.reference_only_weight,
        "environment_reference_id": scene.environment_reference_id,
        "environment_reference_weight": scene.environment_reference_weight,
        "image_asset_id": scene.image_asset_id,
        "candidates": scene.candidates,
    }


def create_scenes(db: Session, storyboard_id: int, scenes_data: list) -> None:
    """Create scenes with tags and character actions for a storyboard."""
    for idx, s_data in enumerate(scenes_data):
        image_url = s_data.image_url
        if image_url and image_url.startswith("data:"):
            image_url = None

        db_scene = Scene(
            storyboard_id=storyboard_id,
            order=idx,
            script=s_data.script,
            speaker=s_data.speaker,
            duration=s_data.duration,
            description=s_data.description,
            image_prompt=s_data.image_prompt,
            image_prompt_ko=s_data.image_prompt_ko,
            negative_prompt=s_data.negative_prompt,
            width=s_data.width,
            height=s_data.height,
            context_tags=s_data.context_tags,
            use_reference_only=s_data.use_reference_only if s_data.use_reference_only is not None else True,
            reference_only_weight=s_data.reference_only_weight or 0.5,
            environment_reference_id=s_data.environment_reference_id,
            environment_reference_weight=s_data.environment_reference_weight or 0.3,
            candidates=s_data.candidates,
        )
        db.add(db_scene)
        db.flush()

        if s_data.tags:
            for t_data in s_data.tags:
                db.add(SceneTag(scene_id=db_scene.id, tag_id=t_data.tag_id, weight=t_data.weight))

        if s_data.character_actions:
            for a_data in s_data.character_actions:
                db.add(
                    SceneCharacterAction(
                        scene_id=db_scene.id,
                        character_id=a_data.character_id,
                        tag_id=a_data.tag_id,
                        weight=a_data.weight,
                    )
                )

        if image_url:
            _link_media_asset(db, db_scene, image_url)


def _link_media_asset(db: Session, db_scene: Scene, image_url: str) -> None:
    """Link or create a MediaAsset for a scene's image_url."""
    from config import MINIO_BUCKET

    path = urlparse(image_url).path
    if path.startswith("/"):
        path = path[1:]
    if path.startswith(f"{MINIO_BUCKET}/"):
        path = path.replace(f"{MINIO_BUCKET}/", "", 1)
    if path.startswith("assets/"):
        path = path.replace("assets/", "", 1)
    storage_key = path

    asset = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()

    if not asset:
        asset = MediaAsset(
            file_type="image",
            storage_key=storage_key,
            file_name=os.path.basename(storage_key),
            mime_type="image/png",
            owner_type="scene",
            owner_id=db_scene.id,
        )
        db.add(asset)
        db.flush()

    db_scene.image_asset_id = asset.id


async def _call_gemini_with_retry(contents: str, config) -> object:
    """Call Gemini API with async + exponential backoff retry (max 2 retries)."""
    delays = [1, 3]
    last_exc = None
    for attempt in range(3):
        try:
            res = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=contents,
                config=config,
            )
            return res
        except Exception as exc:
            last_exc = exc
            error_msg = str(exc)
            is_retryable = "429" in error_msg or "5" in error_msg[:1] and len(error_msg) >= 3
            if attempt < 2 and is_retryable:
                delay = delays[attempt]
                logger.warning("Gemini API retry %d/%d after %ds: %s", attempt + 1, 2, delay, error_msg[:100])
                await asyncio.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]


def _load_character_context(character_id: int, db: Session) -> dict | None:
    """Load character data and classify tags for Gemini template injection."""
    char = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == character_id)
        .first()
    )
    if not char:
        logger.warning("Character %d not found, skipping character context", character_id)
        return None

    identity_tags: list[str] = []
    costume_tags: list[str] = []
    for ct in char.tags:
        tag = ct.tag
        if not tag:
            continue
        layer = tag.default_layer
        if layer is not None and layer <= 3:
            identity_tags.append(tag.name)
        elif layer is not None and 4 <= layer <= 6:
            costume_tags.append(tag.name)

    lora_triggers: list[str] = []
    if char.loras:
        from models.lora import LoRA

        for lora_entry in char.loras:
            lora_id = lora_entry.get("lora_id")
            if not lora_id:
                continue
            lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
            if lora and lora.trigger_words:
                lora_triggers.extend(lora.trigger_words)

    ctx = {
        "name": char.name,
        "gender": char.gender or "female",
        "identity_tags": identity_tags,
        "costume_tags": costume_tags,
        "lora_triggers": lora_triggers,
        "custom_base_prompt": char.custom_base_prompt or "",
    }
    logger.info(
        "[Character Context] %s: identity=%s, costume=%s, lora_triggers=%s",
        char.name,
        identity_tags,
        costume_tags,
        lora_triggers,
    )
    return ctx


async def create_storyboard(request: StoryboardRequest, db: Session | None = None) -> dict:
    """Generate a storyboard from a topic using Gemini (async)."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        is_dialogue = request.structure.lower() == "dialogue"

        # Dialogue validation
        if is_dialogue:
            if not request.character_id:
                raise HTTPException(status_code=400, detail="Dialogue requires character_id (Speaker A)")
            if not request.character_b_id:
                raise HTTPException(status_code=400, detail="Dialogue requires character_b_id (Speaker B)")
            if request.character_id == request.character_b_id:
                raise HTTPException(status_code=400, detail="Speaker A and B must be different characters")

        # Load character context if character_id provided
        character_context = None
        if request.character_id and db:
            character_context = _load_character_context(request.character_id, db)

        # Load character B context for Dialogue
        character_b_context = None
        if is_dialogue and request.character_b_id and db:
            character_b_context = _load_character_context(request.character_b_id, db)

        preset = get_preset_by_structure(request.structure)
        template_name = preset.template if preset else "create_storyboard.j2"
        extra_fields = preset.extra_fields if preset else {}

        template = template_env.get_template(template_name)
        system_instruction = (
            "SYSTEM: You are a professional storyboarder and scriptwriter. "
            "Write clear, engaging scripts in the requested language. "
            "STRICT: Each script must be max 30 chars (Korean) / 60 chars (English) to fit 2 lines on screen. "
            "If a sentence is too long, split it into two scenes. "
            "No emojis. Use ONLY the allowed keywords list for image_prompt tags. "
            "Do not invent new tags. Return raw JSON only."
        )
        rendered = template.render(
            topic=request.topic,
            description=request.description or "",
            duration=request.duration,
            style=request.style,
            structure=request.structure,
            language=request.language,
            actor_a_gender=request.actor_a_gender,
            keyword_context=format_keyword_context(),
            character_context=character_context,
            character_b_context=character_b_context,
            **extra_fields,
        )
        from google.genai import types

        config = types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_NONE",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_NONE",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_NONE",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_NONE",
                ),
            ]
        )
        res = await _call_gemini_with_retry(
            contents=f"{system_instruction}\n\n{rendered}",
            config=config,
        )
        if not res.text:
            # Check why it failed
            error_reason = "Unknown error"
            if res.prompt_feedback and res.prompt_feedback.block_reason:
                error_reason = f"Blocked by safety filters: {res.prompt_feedback.block_reason}"
            elif res.candidates and res.candidates[0].finish_reason:
                error_reason = f"Finished with reason: {res.candidates[0].finish_reason}"

            raise ValueError(f"Gemini returned empty response. Reason: {error_reason}")

        cleaned = strip_markdown_codeblock(res.text)
        scenes = json.loads(cleaned)
        scenes = normalize_scene_tags_key(scenes)

        # Warn if scripts exceed 2-line rendering limit
        MAX_SCRIPT_CHARS = 35
        for s in scenes:
            script = s.get("script", "")
            if len(script) > MAX_SCRIPT_CHARS:
                logger.warning(
                    f"[Scene {s.get('scene_id', '?')}] Script too long for 2 lines: "
                    f"{len(script)} chars (max {MAX_SCRIPT_CHARS}): '{script[:40]}...'"
                )

        for scene in scenes:
            from config import ENABLE_DANBOORU_VALIDATION
            from services.keywords import filter_prompt_tokens
            from services.prompt import (
                normalize_and_fix_tags,
                normalize_prompt_tokens,
                validate_tags_with_danbooru,
            )

            raw_prompt = scene.get("image_prompt", "")
            if not raw_prompt:
                continue

            scene_id = scene.get("scene_id", "?")
            logger.info(f"[Scene {scene_id}] Tag Pipeline Start")
            logger.info(f"  1\ufe0f\u20e3  Raw Gemini: {raw_prompt}")

            normalized = normalize_and_fix_tags(raw_prompt)
            logger.info(f"  2\ufe0f\u20e3  Normalized:  {normalized}")

            if ENABLE_DANBOORU_VALIDATION:
                tags = [t.strip() for t in normalized.split(",") if t.strip()]
                validated_tags = validate_tags_with_danbooru(tags)
                normalized = ", ".join(validated_tags)
                logger.info(f"  3\ufe0f\u20e3  Validated:   {normalized}")

            filtered = filter_prompt_tokens(normalized)
            if not filtered:
                logger.warning("No allowed keywords in scene prompt; using normalized original.")
                filtered = normalize_prompt_tokens(normalized)

            logger.info(f"  4\ufe0f\u20e3  Filtered:    {filtered}")
            logger.info(f"  \u2705 Final Prompt: {filtered}")

            scene["image_prompt"] = filtered

            if not scene.get("negative_prompt"):
                logger.info(f"  \U0001f527 Adding default negative prompt to scene {scene_id}")
                scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT
            else:
                logger.info(
                    f"  \u2139\ufe0f  Scene {scene_id} already has negative_prompt: {scene['negative_prompt'][:50]}..."
                )

        # Auto-pin background based on context_tags.environment
        logger.info("[Storyboard] Auto-pin: Analyzing environment tags for background consistency")
        previous_env_tags = None

        for i, scene in enumerate(scenes):
            context_tags = scene.get("context_tags", {})
            current_env_tags = set(context_tags.get("environment", [])) if context_tags else set()

            if i == 0:
                previous_env_tags = current_env_tags
                logger.info(f"  Scene {i}: First scene, env={list(current_env_tags)}")
                continue

            if current_env_tags and previous_env_tags and (current_env_tags & previous_env_tags):
                scene["_auto_pin_previous"] = True
                logger.info(f"  Scene {i}: Same location {list(current_env_tags)} \u2192 mark for auto-pin")
            else:
                scene["_auto_pin_previous"] = False
                logger.info(
                    f"  Scene {i}: Location changed {list(previous_env_tags)} \u2192 {list(current_env_tags)}, no pin"
                )

            previous_env_tags = current_env_tags

        logger.info(f"[Storyboard] Returning {len(scenes)} scenes with negative prompts")
        for i, s in enumerate(scenes):
            logger.info(f"  Scene {i + 1} negative: {s.get('negative_prompt', 'NONE')[:80]}")
        result = {"scenes": scenes}
        if request.character_id:
            result["character_id"] = request.character_id
        if request.character_b_id:
            result["character_b_id"] = request.character_b_id
        return result
    except Exception as exc:
        # Check if it's a Gemini API quota error
        error_msg = str(exc)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.error("Gemini API quota exhausted")
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exhausted. Please try again later or check your API limits at https://aistudio.google.com/app/apikey",
            ) from exc

        logger.exception("Storyboard generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _sync_speaker_mappings(
    db: Session,
    storyboard_id: int,
    character_id: int | None,
    character_b_id: int | None,
) -> None:
    """Sync speaker→character mappings for a storyboard.

    If character_b_id is provided (Dialogue mode), maps A→character_id, B→character_b_id.
    Otherwise clears all mappings.
    """
    from services.speaker_resolver import assign_speakers

    if not character_b_id:
        assign_speakers(storyboard_id, {}, db)
        return

    speaker_map: dict[str, int] = {}
    if character_id:
        speaker_map["A"] = character_id
    speaker_map["B"] = character_b_id
    assign_speakers(storyboard_id, speaker_map, db)


def save_storyboard_to_db(db: Session, request: StoryboardSave) -> dict:
    """Save a full storyboard and its scenes to the DB."""
    safe_title = truncate_title(request.title)
    logger.info("\U0001f4be [Storyboard Save] %s (truncated from %d chars)", safe_title, len(request.title))

    if not request.group_id:
        raise HTTPException(status_code=400, detail="group_id is required")

    db_storyboard = Storyboard(
        title=safe_title,
        description=request.description,
        group_id=request.group_id,
        caption=request.caption,
    )
    db.add(db_storyboard)
    db.flush()

    create_scenes(db, db_storyboard.id, request.scenes)

    # Save speaker→character mappings if character_b_id is provided (Dialogue)
    _sync_speaker_mappings(db, db_storyboard.id, request.character_id, request.character_b_id)

    db.commit()
    db.refresh(db_storyboard)

    scene_ids = [scene.id for scene in db_storyboard.scenes]

    return {"status": "success", "storyboard_id": db_storyboard.id, "scene_ids": scene_ids}


def list_storyboards_from_db(
    db: Session,
    group_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    """List all storyboards with scene/image counts."""
    from models.group import Group

    query = (
        db.query(Storyboard)
        .options(joinedload(Storyboard.scenes).joinedload(Scene.image_asset))
        .filter(Storyboard.deleted_at.is_(None))
    )
    if group_id is not None:
        query = query.filter(Storyboard.group_id == group_id)
    elif project_id is not None:
        group_ids = [g.id for g in db.query(Group.id).filter(Group.project_id == project_id).all()]
        if group_ids:
            query = query.filter(Storyboard.group_id.in_(group_ids))
        else:
            return []
    storyboards = query.all()

    result = []
    for s in storyboards:
        scenes = s.scenes or []
        result.append(
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "scene_count": len(scenes),
                "image_count": sum(1 for sc in scenes if sc.image_url),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
        )
    return result


def get_storyboard_by_id(db: Session, storyboard_id: int) -> dict:
    """Get a storyboard with all scenes, tags, and character actions."""
    from models.render_history import RenderHistory

    storyboard = (
        db.query(Storyboard)
        .options(
            joinedload(Storyboard.scenes).joinedload(Scene.tags).joinedload(SceneTag.tag),
            joinedload(Storyboard.scenes).joinedload(Scene.character_actions).joinedload(SceneCharacterAction.tag),
            joinedload(Storyboard.scenes).joinedload(Scene.image_asset),
            joinedload(Storyboard.render_history).joinedload(RenderHistory.media_asset),
        )
        .filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None))
        .first()
    )

    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    # Resolve settings from cascade (group_config → project)
    from models.group import Group
    from services.config_resolver import resolve_effective_config

    group = (
        db.query(Group)
        .options(joinedload(Group.config), joinedload(Group.project))
        .filter(Group.id == storyboard.group_id)
        .first()
    )
    effective = resolve_effective_config(group.project, group) if group else {"values": {}}

    scenes = sorted(storyboard.scenes, key=lambda s: s.order)

    recent_videos = [
        {"url": rh.media_asset.url, "label": rh.label, "createdAt": int(rh.created_at.timestamp() * 1000)}
        for rh in storyboard.render_history[:10]
        if rh.created_at
    ]

    # Resolve character_b_id from storyboard_characters
    from services.speaker_resolver import resolve_speaker_to_character

    character_b_id = resolve_speaker_to_character(storyboard.id, "B", db)

    return {
        "id": storyboard.id,
        "title": storyboard.title,
        "description": storyboard.description,
        "group_id": storyboard.group_id,
        "character_id": effective["values"].get("character_id"),
        "character_b_id": character_b_id,
        "style_profile_id": effective["values"].get("style_profile_id"),
        "narrator_voice_preset_id": effective["values"].get("narrator_voice_preset_id"),
        "video_url": storyboard.video_url,
        "recent_videos": recent_videos,
        "caption": storyboard.caption,
        "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
        "updated_at": storyboard.updated_at.isoformat() if storyboard.updated_at else None,
        "scenes": [serialize_scene(sc) for sc in scenes],
    }


def update_storyboard_in_db(db: Session, storyboard_id: int, request: StoryboardSave) -> dict:
    """Update a storyboard by replacing all scenes."""
    storyboard = (
        db.query(Storyboard)
        .options(
            selectinload(Storyboard.scenes),
        )
        .filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None))
        .first()
    )
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    safe_title = truncate_title(request.title)
    logger.info("\u270f\ufe0f [Storyboard Update] id=%d title=%s", storyboard_id, safe_title)

    storyboard.title = safe_title
    storyboard.description = request.description
    if request.group_id is not None:
        storyboard.group_id = request.group_id
    storyboard.caption = request.caption

    # Nullify asset FK references on scenes first
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id).update(
        {Scene.image_asset_id: None, Scene.environment_reference_id: None},
        synchronize_session=False,
    )
    db.flush()

    scene_ids = [s.id for s in db.query(Scene.id).filter(Scene.storyboard_id == storyboard_id).all()]
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id).delete(synchronize_session=False)

    db.query(MediaAsset).filter(
        MediaAsset.owner_type == "storyboard",
        MediaAsset.owner_id == storyboard_id,
    ).delete(synchronize_session=False)

    if scene_ids:
        db.query(MediaAsset).filter(
            MediaAsset.owner_type == "scene",
            MediaAsset.owner_id.in_(scene_ids),
        ).delete(synchronize_session=False)

    db.flush()

    create_scenes(db, storyboard_id, request.scenes)

    # Update speaker→character mappings (Dialogue)
    _sync_speaker_mappings(db, storyboard_id, request.character_id, request.character_b_id)

    db.commit()
    db.refresh(storyboard)
    return {"status": "success", "storyboard_id": storyboard.id}


def update_storyboard_metadata(db: Session, storyboard_id: int, request: StoryboardUpdate) -> dict:
    """Update only storyboard metadata (title, caption, etc) without touching scenes."""
    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f4dd [Storyboard Metadata Update] id=%d", storyboard_id)

    if request.title is not None:
        storyboard.title = truncate_title(request.title)
    if request.description is not None:
        storyboard.description = request.description
    if request.caption is not None:
        storyboard.caption = request.caption

    db.commit()
    return {"status": "success", "storyboard_id": storyboard.id}


def delete_storyboard_from_db(db: Session, storyboard_id: int) -> dict:
    """Soft-delete a storyboard (set deleted_at timestamp)."""
    from datetime import datetime

    storyboard = (
        db.query(Storyboard)
        .filter(
            Storyboard.id == storyboard_id,
            Storyboard.deleted_at.is_(None),
        )
        .first()
    )
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f5d1\ufe0f [Storyboard Soft Delete] id=%d title=%s", storyboard_id, storyboard.title)
    storyboard.deleted_at = datetime.now(UTC)
    db.commit()
    return {"status": "success"}


def permanent_delete_storyboard(db: Session, storyboard_id: int) -> dict:
    """Permanently delete a storyboard and all its scenes (CASCADE) + cleanup assets."""
    storyboard = (
        db.query(Storyboard)
        .options(
            selectinload(Storyboard.scenes),
        )
        .filter(Storyboard.id == storyboard_id)
        .first()
    )
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f5d1\ufe0f [Storyboard Permanent Delete] id=%d title=%s", storyboard_id, storyboard.title)

    try:
        db.query(Scene).filter(Scene.storyboard_id == storyboard_id).update(
            {Scene.image_asset_id: None, Scene.environment_reference_id: None},
            synchronize_session=False,
        )

        # render_history rows are CASCADE-deleted by DB FK
        # Clean up owned media assets
        db.query(MediaAsset).filter(
            MediaAsset.owner_type == "storyboard",
            MediaAsset.owner_id == storyboard_id,
        ).delete(synchronize_session=False)

        scene_ids = [s.id for s in storyboard.scenes]
        if scene_ids:
            db.query(MediaAsset).filter(
                MediaAsset.owner_type == "scene",
                MediaAsset.owner_id.in_(scene_ids),
            ).delete(synchronize_session=False)

        db.delete(storyboard)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        import sys
        import traceback

        traceback.print_exc(file=sys.stderr)
        logger.exception("Failed to permanently delete storyboard %d", storyboard_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}") from e
