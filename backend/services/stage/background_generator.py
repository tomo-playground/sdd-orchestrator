"""Stage Workflow — Background image batch generation.

Reads scene environment tags, groups by location, generates no_humans
background images via SD WebUI, and assigns them to scenes.
"""

from __future__ import annotations

import base64

from sqlalchemy.orm import Session, joinedload

from config import (
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
from services.style_context import extract_style_loras, resolve_style_context

# ── Location extraction ──────────────────────────────────────────────


def extract_locations_from_scenes(scenes: list[Scene]) -> dict[str, dict]:
    """Group scenes by environment tags to derive locations.

    Returns: {location_key: {"name": str, "tags": list[str], "scene_ids": list[int]}}
    """
    loc_map: dict[str, dict] = {}

    for scene in scenes:
        env_tags = (scene.context_tags or {}).get("environment", [])
        if not env_tags:
            continue
        key = "_".join(sorted(env_tags))
        if key not in loc_map:
            loc_map[key] = {
                "name": env_tags[0].replace("_", " ").title(),
                "tags": list(env_tags),
                "scene_ids": [],
            }
        loc_map[key]["scene_ids"].append(scene.id)

    return loc_map


# ── Image generation ─────────────────────────────────────────────────


async def _generate_background_image(
    location_tags: list[str],
    style_loras: list[dict],
    quality_tags: list[str] | None,
    db: Session,
) -> bytes | None:
    """Generate a single no_humans background image via SD WebUI."""
    from schemas import SceneGenerateRequest
    from services.generation import _build_payload, _call_sd_api_raw
    from services.generation_context import GenerationContext
    from services.prompt.v3_composition import V3PromptBuilder

    builder = V3PromptBuilder(db)
    prompt = builder.compose_for_background(
        location_tags=location_tags,
        quality_tags=quality_tags,
        style_loras=style_loras,
    )

    negative = NARRATOR_NEGATIVE_PROMPT_EXTRA
    request = SceneGenerateRequest(prompt=prompt, negative_prompt=negative)
    ctx = GenerationContext(request=request)
    ctx.prompt = prompt
    ctx.negative_prompt = negative

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


async def generate_location_backgrounds(storyboard_id: int, db: Session) -> list[dict]:
    """Generate background images for each location in a storyboard.

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

    locations = extract_locations_from_scenes(scenes)
    if not locations:
        logger.info("[Stage] No locations found for storyboard %d", storyboard_id)
        return []

    # Resolve style context + ensure correct SD checkpoint
    style_ctx = resolve_style_context(storyboard_id, db)
    style_loras = extract_style_loras(style_ctx)
    quality_tags = style_ctx.default_positive.split(", ") if style_ctx and style_ctx.default_positive else None

    if style_ctx and style_ctx.sd_model_name:
        from services.image_generation_core import _ensure_correct_checkpoint

        await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    storyboard.stage_status = STAGE_STATUS_STAGING
    db.commit()

    results: list[dict] = []
    asset_svc = AssetService(db)

    for loc_key, loc_info in locations.items():
        # Check if background already exists
        existing = (
            db.query(Background)
            .filter(
                Background.storyboard_id == storyboard_id,
                Background.location_key == loc_key,
                Background.deleted_at.is_(None),
            )
            .first()
        )
        if existing and existing.image_asset_id:
            results.append({"location_key": loc_key, "background_id": existing.id, "status": "exists"})
            continue

        # Create or reuse Background record
        bg = existing or Background(
            name=loc_info["name"],
            storyboard_id=storyboard_id,
            location_key=loc_key,
            tags=loc_info["tags"],
            is_system=False,
        )
        if not existing:
            db.add(bg)
            db.flush()

        # Generate image
        img_bytes = await _generate_background_image(loc_info["tags"], style_loras, quality_tags, db)
        if not img_bytes:
            results.append({"location_key": loc_key, "background_id": bg.id, "status": "failed"})
            continue

        asset = asset_svc.save_background_image(bg.id, img_bytes)
        bg.image_asset_id = asset.id
        db.commit()

        results.append({"location_key": loc_key, "background_id": bg.id, "status": "generated"})
        logger.info("[Stage] Background generated: %s (ID=%d)", loc_key, bg.id)

    # Update stage status
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
    loc_to_bg: dict[str, dict] = {}
    for bg in backgrounds:
        if bg.location_key:
            loc_to_bg[bg.location_key] = {"id": bg.id, "image_asset_id": bg.image_asset_id}

    assignments: list[dict] = []
    for scene in scenes:
        env_tags = (scene.context_tags or {}).get("environment", [])
        if not env_tags:
            continue
        key = "_".join(sorted(env_tags))
        bg_info = loc_to_bg.get(key)
        if not bg_info:
            continue
        bg_id = bg_info["id"]
        changed = False
        if scene.background_id != bg_id:
            scene.background_id = bg_id
            changed = True
        # Clear old scene-to-scene pin; Stage background takes over
        if scene.environment_reference_id:
            scene.environment_reference_id = None
            changed = True
        if changed:
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
    quality_tags = style_ctx.default_positive.split(", ") if style_ctx and style_ctx.default_positive else None

    if style_ctx and style_ctx.sd_model_name:
        from services.image_generation_core import _ensure_correct_checkpoint

        await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    img_bytes = await _generate_background_image(bg.tags or [], style_loras, quality_tags, db)
    if not img_bytes:
        return {"background_id": bg.id, "status": "failed"}

    asset_svc = AssetService(db)
    asset = asset_svc.save_background_image(bg.id, img_bytes)
    bg.image_asset_id = asset.id
    db.commit()

    logger.info("[Stage] Background regenerated: %s (ID=%d)", location_key, bg.id)
    return {"background_id": bg.id, "status": "regenerated"}
