"""Stage Workflow — Background image batch generation.

Reads scene environment tags, groups by location, generates no_humans
background images via SD WebUI, and assigns them to scenes.
"""

from __future__ import annotations

import asyncio
import base64

from sqlalchemy.orm import Session, joinedload

from config import (
    DEFAULT_SCENE_NEGATIVE_PROMPT,
    NARRATOR_NEGATIVE_PROMPT_EXTRA,
    STAGE_STATUS_FAILED,
    STAGE_STATUS_STAGED,
    STAGE_STATUS_STAGING,
    logger,
)
from models.background import Background
from models.scene import Scene
from models.storyboard import Storyboard
from services.asset_service import AssetService
from services.stage.background_location import (
    compute_location_key,
    extract_locations_from_scenes,
    find_best_matching_bg,
    resolve_bg_quality_tags,
)
from services.style_context import extract_style_loras, resolve_style_context

# ── Image generation ─────────────────────────────────────────────────


def _prepare_bg_prompt(
    location_tags: list[str],
    style_loras: list[dict],
    quality_tags: list[str] | None,
    negative_tags: str | None,
    db: Session,
    *,
    style_ctx=None,
) -> dict:
    """Prepare background prompt data (requires DB for PromptBuilder).

    Returns dict with prompt, negative, style_ctx, style_loras for SD call.
    """
    from services.prompt.composition import PromptBuilder

    builder = PromptBuilder(db)
    prompt = builder.compose_for_background(
        location_tags=location_tags,
        quality_tags=quality_tags,
        style_loras=style_loras,
    )

    negative = f"{DEFAULT_SCENE_NEGATIVE_PROMPT}, {NARRATOR_NEGATIVE_PROMPT_EXTRA}"
    if negative_tags:
        negative = f"{negative}, {negative_tags}"

    return {"prompt": prompt, "negative": negative, "style_ctx": style_ctx, "style_loras": style_loras}


async def _generate_bg_from_prompt(prompt_data: dict) -> bytes | None:
    """Generate a background image from pre-built prompt data (no DB needed)."""
    from schemas import SceneGenerateRequest
    from services.generation import _adjust_parameters, _build_payload, _call_sd_api_raw
    from services.generation_context import GenerationContext

    prompt = prompt_data["prompt"]
    negative = prompt_data["negative"]
    style_ctx = prompt_data["style_ctx"]
    style_loras = prompt_data["style_loras"]

    request = SceneGenerateRequest(prompt=prompt, negative_prompt=negative)
    ctx = GenerationContext(request=request)
    ctx.style_context = style_ctx
    ctx.style_loras = style_loras
    ctx.prompt = prompt
    ctx.negative_prompt = negative

    _adjust_parameters(ctx)
    payload = _build_payload(ctx)
    logger.info("[Stage] Generating background: %s", prompt[:120])

    try:
        result = await _call_sd_api_raw(payload, ctx)
        img_b64 = result.get("image")
        if img_b64:
            return base64.b64decode(img_b64)
    except Exception as e:
        logger.error("[Stage] Background generation failed: %s", e)
    return None


# ── Public API ───────────────────────────────────────────────────────


async def _process_single_location(
    loc_key: str,
    loc_info: dict,
    storyboard_id: int,
    style_profile_id: int | None,
    style_loras: list[dict],
    quality_tags: list[str] | None,
    negative_tags: str | None,
    style_ctx,
    db: Session,
    *,
    force: bool = False,
) -> dict:
    """Process a single location: DB check → prompt build → SD call → save.

    Splits DB usage and SD API call to avoid long connection pool hold.
    """
    # Phase 1: DB — check existing / create record / build prompt
    existing_q = db.query(Background).filter(
        Background.storyboard_id == storyboard_id,
        Background.location_key == loc_key,
        Background.deleted_at.is_(None),
    )
    if style_profile_id is not None:
        existing_q = existing_q.filter(Background.style_profile_id == style_profile_id)
    else:
        existing_q = existing_q.filter(Background.style_profile_id.is_(None))
    existing = existing_q.first()

    if existing and existing.image_asset_id and not force:
        return {"location_key": loc_key, "background_id": existing.id, "status": "exists"}

    bg = existing or Background(
        name=loc_info["name"],
        storyboard_id=storyboard_id,
        location_key=loc_key,
        tags=loc_info["tags"],
        is_system=False,
        style_profile_id=style_profile_id,
    )
    if not existing:
        db.add(bg)
        db.flush()
    bg_id = bg.id

    prompt_data = _prepare_bg_prompt(
        loc_info["tags"],
        style_loras,
        quality_tags,
        negative_tags,
        db,
        style_ctx=style_ctx,
    )
    db.commit()  # Release DB connection before SD call

    # Phase 2: SD API call (no DB needed, 30-60s)
    img_bytes = await _generate_bg_from_prompt(prompt_data)
    if not img_bytes:
        return {"location_key": loc_key, "background_id": bg_id, "status": "failed"}

    # Phase 3: Save result (DB auto-reconnects)
    asset_svc = AssetService(db)
    asset = asset_svc.save_background_image(bg_id, img_bytes)
    bg_fresh = db.get(Background, bg_id)
    bg_fresh.image_asset_id = asset.id
    db.commit()
    logger.info("[Stage] Background generated: %s (ID=%d)", loc_key, bg_id)
    return {"location_key": loc_key, "background_id": bg_id, "status": "generated"}


async def generate_location_backgrounds(storyboard_id: int, db: Session, *, force: bool = False) -> list[dict]:
    """Generate background images for each location in a storyboard.

    Args:
        force: If True, regenerate images even when they already exist.

    Returns list of {location_key, background_id, status} dicts.
    """
    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not storyboard:
        raise ValueError(f"Storyboard {storyboard_id} not found")

    scenes = (
        db.query(Scene)
        .filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )
    if not scenes:
        return []

    locations = extract_locations_from_scenes(scenes, db)
    if not locations:
        has_any_env = any((s.context_tags or {}).get("environment") for s in scenes)
        if not has_any_env:
            logger.warning(
                "[Stage] No environment tags in scenes for storyboard %d (Express mode?)",
                storyboard_id,
            )
        else:
            logger.info("[Stage] No locations found for storyboard %d", storyboard_id)
        return []

    # Resolve style context + ensure correct SD checkpoint
    style_ctx = resolve_style_context(storyboard_id, db)
    style_loras = extract_style_loras(style_ctx)
    quality_tags = resolve_bg_quality_tags(style_ctx)
    negative_tags = style_ctx.default_negative if style_ctx else None
    style_profile_id = style_ctx.profile_id if style_ctx else None

    if style_ctx and style_ctx.sd_model_name:
        from services.image_generation_core import _ensure_correct_checkpoint

        await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    storyboard.stage_status = STAGE_STATUS_STAGING
    db.commit()

    tasks = [
        _process_single_location(
            loc_key,
            loc_info,
            storyboard_id,
            style_profile_id,
            style_loras,
            quality_tags,
            negative_tags,
            style_ctx,
            db,
            force=force,
        )
        for loc_key, loc_info in locations.items()
    ]
    results: list[dict] = list(await asyncio.gather(*tasks))

    # Update stage status (re-fetch after commits in _process_single_location)
    storyboard = db.get(Storyboard, storyboard_id)
    failed = sum(1 for r in results if r["status"] == "failed")
    storyboard.stage_status = STAGE_STATUS_FAILED if failed == len(results) else STAGE_STATUS_STAGED
    db.commit()

    return results


def assign_backgrounds_to_scenes(storyboard_id: int, db: Session) -> list[dict]:
    """Assign background_id to scenes matching the same location_key.

    Returns list of {scene_id, background_id, location_key} dicts.
    """
    scenes = (
        db.query(Scene)
        .filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )

    # Prefer backgrounds matching the current style_profile
    style_ctx = resolve_style_context(storyboard_id, db)
    current_style_id = style_ctx.profile_id if style_ctx else None

    backgrounds = (
        db.query(Background)
        .filter(
            Background.storyboard_id == storyboard_id,
            Background.deleted_at.is_(None),
            Background.image_asset_id.isnot(None),
        )
        .all()
    )

    # Build location_key → {background_id, image_asset_id} map
    # Prefer current style; fallback to any style
    loc_to_bg: dict[str, dict] = {}
    for bg in backgrounds:
        if not bg.location_key:
            continue
        entry = {"id": bg.id, "image_asset_id": bg.image_asset_id}
        existing = loc_to_bg.get(bg.location_key)
        if not existing or bg.style_profile_id == current_style_id:
            loc_to_bg[bg.location_key] = entry

    from services.keywords.db_cache import TagAliasCache

    TagAliasCache.initialize(db)
    assignments: list[dict] = []
    for scene in scenes:
        env_tags = (scene.context_tags or {}).get("environment", [])
        if not env_tags:
            continue
        # Use same location-only key logic as extract_locations_from_scenes
        key = compute_location_key(env_tags, db)
        bg_info = loc_to_bg.get(key)
        if not bg_info:
            # Fallback: find best matching BG via subset/overlap
            bg_info, key = find_best_matching_bg(key, loc_to_bg)
        if not bg_info:
            continue
        bg_id = bg_info["id"]
        if scene.background_id != bg_id:
            scene.background_id = bg_id
            assignments.append({"scene_id": scene.id, "background_id": bg_id, "location_key": key})

    if assignments:
        db.commit()
        logger.info("[Stage] Assigned %d scenes to backgrounds", len(assignments))

    return assignments


async def regenerate_background(
    storyboard_id: int,
    location_key: str,
    db: Session,
    *,
    tags: list[str] | None = None,
) -> dict:
    """Regenerate a specific location's background image.

    If *tags* is provided, update the background tags before regenerating.
    Returns {background_id, status}.
    """
    bg = (
        db.query(Background)
        .options(joinedload(Background.image_asset))
        .filter(
            Background.storyboard_id == storyboard_id,
            Background.location_key == location_key,
            Background.deleted_at.is_(None),
        )
        .first()
    )
    if not bg:
        # Auto-create Background record when individual generate is called first
        loc_tags = tags or location_key.split("_")
        bg = Background(
            name=loc_tags[0].replace("_", " ").title(),
            storyboard_id=storyboard_id,
            location_key=location_key,
            tags=loc_tags,
            is_system=False,
        )
        db.add(bg)
        db.flush()

    # Update tags if provided
    if tags is not None:
        bg.tags = tags
        db.flush()

    style_ctx = resolve_style_context(storyboard_id, db)
    style_loras = extract_style_loras(style_ctx)
    quality_tags = resolve_bg_quality_tags(style_ctx)
    negative_tags = style_ctx.default_negative if style_ctx else None

    if style_ctx and style_ctx.sd_model_name:
        from services.image_generation_core import _ensure_correct_checkpoint

        await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    # Phase 1: Build prompt (DB needed), then release connection
    bg_id = bg.id
    bg_tags = list(bg.tags or [])
    prompt_data = _prepare_bg_prompt(
        bg_tags,
        style_loras,
        quality_tags,
        negative_tags,
        db,
        style_ctx=style_ctx,
    )
    db.commit()

    # Phase 2: SD call (no DB needed, 30-60s)
    img_bytes = await _generate_bg_from_prompt(prompt_data)
    if not img_bytes:
        return {"background_id": bg_id, "status": "failed"}

    # Phase 3: Save result (DB auto-reconnects)
    bg_fresh = db.get(Background, bg_id)
    bg_fresh.style_profile_id = style_ctx.profile_id if style_ctx else None
    asset_svc = AssetService(db)
    asset = asset_svc.save_background_image(bg_id, img_bytes)
    bg_fresh.image_asset_id = asset.id
    db.commit()

    logger.info("[Stage] Background regenerated: %s (ID=%d)", location_key, bg_id)
    return {"background_id": bg_id, "status": "regenerated"}
