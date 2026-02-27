"""Stage Workflow — Background image batch generation.

Reads scene environment tags, groups by location, generates no_humans
background images via SD WebUI, and assigns them to scenes.
"""

from __future__ import annotations

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

# Anti-realistic tags to force anime style for backgrounds
_ANTI_REALISTIC_NEGATIVE = "realistic, photorealistic, photo, 3d, render, cgi, photograph"
# Anti-sepia: prevent washed-out monochrome backgrounds
_ANTI_SEPIA_NEGATIVE = "monochrome, sepia, desaturated, washed_out, greyscale, faded"
from models.background import Background
from models.scene import Scene
from models.storyboard import Storyboard
from models.tag import Tag
from services.asset_service import AssetService
from services.keywords.db_cache import TagAliasCache
from services.style_context import extract_style_loras, resolve_style_context

# ── Location extraction ──────────────────────────────────────────────

_LOCATION_GROUP_PREFIX = "location_"


def _find_best_matching_bg(
    scene_key: str, loc_to_bg: dict[str, dict]
) -> tuple[dict | None, str]:
    """Find the best matching BG when exact key doesn't match (subset/overlap)."""
    scene_set = set(scene_key.split("_"))
    best_info, best_key, best_score = None, scene_key, 0.0
    for bg_key, bg_info in loc_to_bg.items():
        bg_set = set(bg_key.split("_"))
        overlap = len(scene_set & bg_set) / len(scene_set | bg_set)
        if (scene_set <= bg_set or bg_set <= scene_set or overlap > 0.5) and overlap > best_score:
            best_info, best_key, best_score = bg_info, bg_key, overlap
    return best_info, best_key


def _filter_location_tags(env_tags: list[str], db: Session) -> list[str]:
    """Filter environment tags to location-only (group_name starts with 'location_')."""
    if not env_tags:
        return []
    normed = [t.lower().strip() for t in env_tags]
    rows = db.query(Tag.name).filter(Tag.name.in_(normed), Tag.group_name.like(f"{_LOCATION_GROUP_PREFIX}%")).all()
    return [r.name for r in rows]


def _resolve_location_aliases(tags: list[str]) -> list[str]:
    """Apply tag alias resolution for location grouping (e.g. coffee_shop → cafe)."""
    resolved = []
    for tag in tags:
        replacement = TagAliasCache.get_replacement(tag)
        resolved.append(replacement if isinstance(replacement, str) else tag)
    return resolved


def extract_locations_from_scenes(scenes: list[Scene], db: Session) -> dict[str, dict]:
    """Group scenes by location tags (excluding props) to derive locations.

    Uses Tag.group_name 'location_*' filter + alias resolution for accurate grouping.
    Returns: {location_key: {"name": str, "tags": list[str], "scene_ids": list[int]}}
    """
    TagAliasCache.initialize(db)
    loc_map: dict[str, dict] = {}

    for scene in scenes:
        env_tags = (scene.context_tags or {}).get("environment", [])
        if not env_tags:
            continue
        # Filter to location-type tags only, then resolve aliases
        loc_tags = _filter_location_tags(env_tags, db)
        if not loc_tags:
            loc_tags = env_tags[:1]  # fallback: use first tag
        loc_tags = _resolve_location_aliases(loc_tags)
        key = "_".join(sorted(set(loc_tags)))
        if key not in loc_map:
            loc_map[key] = {
                "name": loc_tags[0].replace("_", " ").title(),
                "tags": list(env_tags),  # keep ALL tags for image generation
                "scene_ids": [],
            }
        else:
            # Merge env_tags: union of all tags across scenes in same location
            existing = set(loc_map[key]["tags"])
            for t in env_tags:
                if t not in existing:
                    loc_map[key]["tags"].append(t)
                    existing.add(t)
        loc_map[key]["scene_ids"].append(scene.id)

    return _merge_subset_locations(loc_map)


def _merge_subset_locations(loc_map: dict[str, dict]) -> dict[str, dict]:
    """Merge locations whose key tags are a subset of a larger location."""
    if len(loc_map) <= 1:
        return loc_map

    keys = sorted(loc_map.keys(), key=lambda k: len(loc_map[k]["scene_ids"]), reverse=True)
    merged: dict[str, dict] = {}
    absorbed: set[str] = set()

    for key in keys:
        if key in absorbed:
            continue
        key_set = set(key.split("_"))
        merged[key] = loc_map[key]
        # Absorb smaller locations whose tags overlap significantly
        for other in keys:
            if other == key or other in absorbed:
                continue
            other_set = set(other.split("_"))
            # Merge if one is a subset of the other, or Jaccard similarity > 0.5
            overlap = len(key_set & other_set) / len(key_set | other_set)
            if key_set <= other_set or other_set <= key_set or overlap > 0.5:
                merged[key]["scene_ids"].extend(loc_map[other]["scene_ids"])
                for t in loc_map[other]["tags"]:
                    if t not in merged[key]["tags"]:
                        merged[key]["tags"].append(t)
                absorbed.add(other)
                logger.info("[Stage] Merged location '%s' into '%s' (overlap=%.2f)", other, key, overlap)

    return merged


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

    negative = f"{DEFAULT_SCENE_NEGATIVE_PROMPT}, {NARRATOR_NEGATIVE_PROMPT_EXTRA}, {_ANTI_SEPIA_NEGATIVE}"
    if V3PromptBuilder._is_anime_style(quality_tags):
        negative = f"{negative}, {_ANTI_REALISTIC_NEGATIVE}"
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

    locations = extract_locations_from_scenes(scenes, db)
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

    TagAliasCache.initialize(db)
    assignments: list[dict] = []
    for scene in scenes:
        env_tags = (scene.context_tags or {}).get("environment", [])
        if not env_tags:
            continue
        # Use same location-only key logic as extract_locations_from_scenes
        loc_tags = _filter_location_tags(env_tags, db)
        if not loc_tags:
            loc_tags = env_tags[:1]
        loc_tags = _resolve_location_aliases(loc_tags)
        key = "_".join(sorted(set(loc_tags)))
        bg_info = loc_to_bg.get(key)
        if not bg_info:
            # Fallback: find best matching BG via subset/overlap
            bg_info, key = _find_best_matching_bg(key, loc_to_bg)
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
