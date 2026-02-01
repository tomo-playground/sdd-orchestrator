from __future__ import annotations

import asyncio
import json
import os
import re
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from models.associations import SceneCharacterAction, SceneTag
from models.media_asset import MediaAsset
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import StoryboardRequest, StoryboardSave
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
        "steps": scene.steps,
        "cfg_scale": scene.cfg_scale,
        "sampler_name": scene.sampler_name,
        "seed": scene.seed,
        "clip_skip": scene.clip_skip,
        "context_tags": scene.context_tags,
        "tags": [{"tag_id": t.tag_id, "weight": t.weight} for t in scene.tags],
        "character_actions": [
            {"character_id": a.character_id, "tag_id": a.tag_id, "weight": a.weight}
            for a in scene.character_actions
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
            steps=s_data.steps,
            cfg_scale=s_data.cfg_scale,
            sampler_name=s_data.sampler_name,
            seed=s_data.seed,
            clip_skip=s_data.clip_skip,
            context_tags=s_data.context_tags,
            use_reference_only=int(s_data.use_reference_only) if s_data.use_reference_only is not None else 1,
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
                db.add(SceneCharacterAction(
                    scene_id=db_scene.id,
                    character_id=a_data.character_id,
                    tag_id=a_data.tag_id,
                    weight=a_data.weight,
                ))

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
            owner_id=db_scene.id
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


async def create_storyboard(request: StoryboardRequest) -> dict:
    """Generate a storyboard from a topic using Gemini (async)."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        preset = get_preset_by_structure(request.structure)
        template_name = preset.template if preset else "create_storyboard.j2"
        extra_fields = preset.extra_fields if preset else {}

        template = template_env.get_template(template_name)
        system_instruction = (
            "SYSTEM: You are a professional storyboarder and scriptwriter. "
            "Write clear, engaging scripts in the requested language (max 80 chars, max 2 lines). "
            "No emojis. Use ONLY the allowed keywords list for image_prompt tags. "
            "Do not invent new tags. Return raw JSON only."
        )
        rendered = template.render(
            topic=request.topic,
            duration=request.duration,
            style=request.style,
            structure=request.structure,
            language=request.language,
            actor_a_gender=request.actor_a_gender,
            keyword_context=format_keyword_context(),
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
                logger.info(f"  \u2139\ufe0f  Scene {scene_id} already has negative_prompt: {scene['negative_prompt'][:50]}...")

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
                logger.info(f"  Scene {i}: Location changed {list(previous_env_tags)} \u2192 {list(current_env_tags)}, no pin")

            previous_env_tags = current_env_tags

        logger.info(f"[Storyboard] Returning {len(scenes)} scenes with negative prompts")
        for i, s in enumerate(scenes):
            logger.info(f"  Scene {i+1} negative: {s.get('negative_prompt', 'NONE')[:80]}")
        return {"scenes": scenes}
    except Exception as exc:
        # Check if it's a Gemini API quota error
        error_msg = str(exc)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.error("Gemini API quota exhausted")
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exhausted. Please try again later or check your API limits at https://aistudio.google.com/app/apikey"
            ) from exc

        logger.exception("Storyboard generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def save_storyboard_to_db(db: Session, request: StoryboardSave) -> dict:
    """Save a full storyboard and its scenes to the DB."""
    safe_title = truncate_title(request.title)
    logger.info("\U0001f4be [Storyboard Save] %s (truncated from %d chars)", safe_title, len(request.title))

    db_storyboard = Storyboard(
        title=safe_title,
        description=request.description,
        default_character_id=request.default_character_id,
        default_style_profile_id=request.default_style_profile_id,
        default_caption=request.default_caption,
    )
    db.add(db_storyboard)
    db.flush()

    create_scenes(db, db_storyboard.id, request.scenes)

    db.commit()
    db.refresh(db_storyboard)

    scene_ids = [scene.id for scene in db_storyboard.scenes]

    return {
        "status": "success",
        "storyboard_id": db_storyboard.id,
        "scene_ids": scene_ids
    }


def list_storyboards_from_db(db: Session) -> list[dict]:
    """List all storyboards with scene/image counts."""
    storyboards = db.query(Storyboard).options(
        joinedload(Storyboard.scenes).joinedload(Scene.image_asset)
    ).all()

    result = []
    for s in storyboards:
        scenes = s.scenes or []
        result.append({
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "scene_count": len(scenes),
            "image_count": sum(1 for sc in scenes if sc.image_url),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return result


def get_storyboard_by_id(db: Session, storyboard_id: int) -> dict:
    """Get a storyboard with all scenes, tags, and character actions."""
    storyboard = (
        db.query(Storyboard)
        .options(
            joinedload(Storyboard.scenes).joinedload(Scene.tags).joinedload(SceneTag.tag),
            joinedload(Storyboard.scenes).joinedload(Scene.character_actions).joinedload(SceneCharacterAction.tag),
            joinedload(Storyboard.scenes).joinedload(Scene.image_asset),
        )
        .filter(Storyboard.id == storyboard_id)
        .first()
    )

    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    scenes = sorted(storyboard.scenes, key=lambda s: s.order)

    recent_videos = []
    if storyboard.recent_videos_json:
        try:
            recent_videos = json.loads(storyboard.recent_videos_json)
        except Exception:
            recent_videos = []

    return {
        "id": storyboard.id,
        "title": storyboard.title,
        "description": storyboard.description,
        "default_character_id": storyboard.default_character_id,
        "default_style_profile_id": storyboard.default_style_profile_id,
        "video_url": storyboard.video_url,
        "recent_videos": recent_videos,
        "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
        "updated_at": storyboard.updated_at.isoformat() if storyboard.updated_at else None,
        "scenes": [serialize_scene(sc) for sc in scenes],
    }


def update_storyboard_in_db(db: Session, storyboard_id: int, request: StoryboardSave) -> dict:
    """Update a storyboard by replacing all scenes."""
    storyboard = db.query(Storyboard).options(
        selectinload(Storyboard.scenes),
    ).filter(Storyboard.id == storyboard_id).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    safe_title = truncate_title(request.title)
    logger.info("\u270f\ufe0f [Storyboard Update] id=%d title=%s", storyboard_id, safe_title)

    storyboard.title = safe_title
    storyboard.description = request.description
    storyboard.default_character_id = request.default_character_id
    storyboard.default_style_profile_id = request.default_style_profile_id
    storyboard.default_caption = request.default_caption

    # Nullify asset FK references on scenes first
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id).update(
        {Scene.image_asset_id: None, Scene.environment_reference_id: None},
        synchronize_session=False,
    )
    db.flush()

    scene_ids = [
        s.id for s in db.query(Scene.id).filter(Scene.storyboard_id == storyboard_id).all()
    ]
    db.query(Scene).filter(
        Scene.storyboard_id == storyboard_id
    ).delete(synchronize_session=False)

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

    db.commit()
    db.refresh(storyboard)
    return {"status": "success", "storyboard_id": storyboard.id}


def delete_storyboard_from_db(db: Session, storyboard_id: int) -> dict:
    """Delete a storyboard and all its scenes (CASCADE) + cleanup assets."""
    storyboard = db.query(Storyboard).options(
        selectinload(Storyboard.scenes),
    ).filter(Storyboard.id == storyboard_id).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f5d1\ufe0f [Storyboard Delete] id=%d title=%s", storyboard_id, storyboard.title)

    try:
        db.query(Scene).filter(Scene.storyboard_id == storyboard_id).update(
            {Scene.image_asset_id: None, Scene.environment_reference_id: None},
            synchronize_session=False,
        )

        if storyboard.video_asset_id:
            db.query(MediaAsset).filter(MediaAsset.id == storyboard.video_asset_id).delete(synchronize_session=False)

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
        logger.exception("Failed to delete storyboard %d", storyboard_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")
