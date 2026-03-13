"""Character reference image generation, enhancement, and editing.

All functions are async — they call external APIs (SD WebUI, Gemini Imagen)
that may take 30-60s.

db.close() pattern: SQLAlchemy Session.close() returns the connection to the
pool. On the next query the Session transparently acquires a new connection.
We close before long external calls to avoid holding a DB connection idle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from config import (
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    SD_DEFAULT_CLIP_SKIP,
    SD_DEFAULT_SAMPLER,
    SD_REFERENCE_CFG_SCALE,
    SD_REFERENCE_CONTROLNET_MODE,
    SD_REFERENCE_CONTROLNET_POSE,
    SD_REFERENCE_CONTROLNET_WEIGHT,
    SD_REFERENCE_DENOISING,
    SD_REFERENCE_HR_UPSCALER,
    SD_REFERENCE_STEPS,
    logger,
)
from models import Character, CharacterTag, Tag
from schemas import (
    AssignPreviewRequest,
    CandidateImage,
    CharacterPreviewRequest,
    SceneGenerateRequest,
)

if TYPE_CHECKING:
    from services.style_context import StyleContext


def _build_reference_negative(
    style_ctx: StyleContext | None,
    character_negative: list[str] | None,
) -> str:
    """Build negative prompt for character preview.

    With StyleContext: default_negative + negative embeddings + character negative.
    Without: DEFAULT_REFERENCE_NEGATIVE_PROMPT + character negative.

    Cf. generation_style._compose_negative() — always requires StyleContext,
    no fallback to DEFAULT, no dedup (Scene negative comes from different source).
    """
    # Always include DEFAULT_REFERENCE_NEGATIVE_PROMPT (multi-view/background suppressors)
    parts: list[str] = [DEFAULT_REFERENCE_NEGATIVE_PROMPT]
    if style_ctx:
        if style_ctx.default_negative:
            parts.append(style_ctx.default_negative)
        if style_ctx.negative_embeddings:
            parts.append(", ".join(style_ctx.negative_embeddings))

    if character_negative:
        existing = ", ".join(parts)
        extras = [n for n in character_negative if n not in existing]
        if extras:
            parts.append(", ".join(extras))

    return ", ".join(parts)


def _resolve_quality_tags_for_character(character: Character, db: Session) -> list[str] | None:
    """Resolve StyleProfile quality tags for a character via group_id.

    Character → Group → StyleProfile.default_positive

    Returns parsed default_positive tokens, or None if no StyleProfile is configured.
    """
    from services.prompt import split_prompt_tokens
    from services.style_context import resolve_style_context_from_group

    ctx = resolve_style_context_from_group(character.group_id, db)
    if ctx and ctx.default_positive:
        return split_prompt_tokens(ctx.default_positive)

    return None


def _get_character_for_reference(db: Session, character_id: int, *, with_tags: bool = False) -> Character:
    """Fetch character with validation for preview operations."""
    query = db.query(Character)
    if with_tags:
        query = query.options(joinedload(Character.tags).joinedload(CharacterTag.tag))
    character = query.filter(Character.id == character_id, Character.deleted_at.is_(None)).first()
    if not character:
        raise ValueError("Character not found")
    return character


def _save_reference_asset(db: Session, character_id: int, image_bytes: bytes) -> tuple[str, int]:
    """Save image bytes as a reference asset and update the character. Returns (url, asset_id)."""
    from services.asset_service import AssetService

    asset_service = AssetService(db)
    asset = asset_service.save_character_preview(character_id, image_bytes)
    rows = (
        db.query(Character)
        .filter(
            Character.id == character_id,
            Character.deleted_at.is_(None),
        )
        .update({"reference_image_asset_id": asset.id})
    )
    if rows == 0:
        db.rollback()
        raise ValueError(f"Character {character_id} not found or deleted")
    db.commit()
    return asset.url, asset.id


async def regenerate_reference(
    db: Session,
    character_id: int,
    *,
    controlnet_pose: str | None = None,
    num_candidates: int = 1,
) -> dict:
    """Regenerate the character's reference image using 12-Layer prompt system."""
    from services.generation import generate_scene_image
    from services.image import decode_data_url
    from services.prompt.composition import PromptBuilder
    from services.style_context import resolve_style_context_from_group

    character = _get_character_for_reference(db, character_id, with_tags=True)

    # Resolve StyleProfile quality tags (Group → Config → StyleProfile.default_positive)
    quality_tags = _resolve_quality_tags_for_character(character, db)

    # Resolve StyleContext via Group (needed for reference_env_tags/camera_tags + negative)
    style_ctx = resolve_style_context_from_group(character.group_id, db)

    builder = PromptBuilder(db)
    full_prompt = builder.compose_for_reference(character, quality_tags=quality_tags, style_ctx=style_ctx)
    if character.negative_prompt:
        neg_prompt = character.negative_prompt
    else:
        neg_prompt = _build_reference_negative(style_ctx, None)
    # Always merge DEFAULT (covers custom negative_prompt branch where _build_reference_negative was NOT called)
    existing_tags = {t.strip() for t in neg_prompt.split(",")}
    for tag in DEFAULT_REFERENCE_NEGATIVE_PROMPT.split(", "):
        if tag and tag not in existing_tags:
            neg_prompt += ", " + tag

    # Ensure SD WebUI is using the correct checkpoint for this StyleProfile
    if style_ctx and style_ctx.sd_model_name:
        from services.image_generation_core import _ensure_correct_checkpoint

        await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    # StyleProfile generation parameters (override global defaults)
    steps = style_ctx.default_steps if (style_ctx and style_ctx.default_steps is not None) else SD_REFERENCE_STEPS
    cfg_scale = (
        style_ctx.default_cfg_scale
        if (style_ctx and style_ctx.default_cfg_scale is not None)
        else SD_REFERENCE_CFG_SCALE
    )
    sampler_name = (
        style_ctx.default_sampler_name if (style_ctx and style_ctx.default_sampler_name) else SD_DEFAULT_SAMPLER
    )
    clip_skip = (
        style_ctx.default_clip_skip if (style_ctx and style_ctx.default_clip_skip is not None) else SD_DEFAULT_CLIP_SKIP
    )
    enable_hr = style_ctx.default_enable_hr if (style_ctx and style_ctx.default_enable_hr is not None) else False

    pose = controlnet_pose or SD_REFERENCE_CONTROLNET_POSE
    use_cn = bool(pose)

    # Release DB connection before long SD WebUI call (~30-60s)
    db.close()

    candidates: list[CandidateImage] = []
    for i in range(num_candidates):
        request = SceneGenerateRequest(
            prompt=full_prompt,
            negative_prompt=neg_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler_name=sampler_name,
            clip_skip=clip_skip,
            width=512,
            height=768,
            seed=-1,
            enable_hr=enable_hr,
            hr_scale=1.5 if enable_hr else 1.0,
            hr_upscaler=SD_REFERENCE_HR_UPSCALER,
            denoising_strength=SD_REFERENCE_DENOISING if enable_hr else 0.0,
            use_controlnet=use_cn,
            controlnet_pose=pose if use_cn else None,
            controlnet_weight=SD_REFERENCE_CONTROLNET_WEIGHT,
            controlnet_control_mode=SD_REFERENCE_CONTROLNET_MODE,
        )
        res = await generate_scene_image(request)
        if "image" not in res:
            logger.warning("[Preview] Candidate %d failed, skipping", i + 1)
            continue
        if request.use_controlnet and not res.get("controlnet_pose"):
            logger.warning("[Preview] ControlNet requested but not applied — check SD WebUI ControlNet extension")
        candidates.append(CandidateImage(image=res["image"], seed=res.get("seed", -1)))

    if not candidates:
        raise RuntimeError("Generation failed: no candidates produced")

    # Save first candidate as the preview (backward compat)
    image_bytes = decode_data_url(f"data:image/png;base64,{candidates[0].image}")
    url, _ = _save_reference_asset(db, character_id, image_bytes)
    return {
        "ok": True,
        "url": url,
        "candidates": [c.model_dump() for c in candidates],
    }


async def enhance_preview(db: Session, character_id: int) -> dict:
    """Enhance the character's preview image using Gemini Imagen."""
    from services.image import decode_data_url, load_as_data_url
    from services.imagen_edit import get_imagen_service

    character = _get_character_for_reference(db, character_id)
    if not character.reference_image_url:
        raise ValueError("No preview image to enhance")

    image_b64 = load_as_data_url(character.reference_image_url)

    # Release DB connection before long Gemini API call
    db.close()

    service = get_imagen_service()
    result = await service.enhance_image(image_b64)

    # Session auto-reconnects on next use
    enhanced_bytes = decode_data_url(f"data:image/png;base64,{result['enhanced_image']}")
    url, _ = _save_reference_asset(db, character_id, enhanced_bytes)
    return {"ok": True, "url": url, "cost_usd": result["cost_usd"]}


async def edit_preview(db: Session, character_id: int, instruction: str) -> dict:
    """Edit the character's preview image with a natural language instruction via Gemini."""
    from services.image import decode_data_url, load_as_data_url
    from services.imagen_edit import get_imagen_service

    character = _get_character_for_reference(db, character_id, with_tags=True)
    if not character.reference_image_url:
        raise ValueError("No preview image to edit")

    image_b64 = load_as_data_url(character.reference_image_url)
    tag_names = [ct.tag.name for ct in character.tags if ct.tag]
    original_prompt = ", ".join(tag_names) if tag_names else ""

    # Release DB connection before long Gemini API call
    db.close()

    service = get_imagen_service()
    result = await service.edit_with_analysis(
        image_b64=image_b64,
        original_prompt=original_prompt,
        target_change=instruction,
    )

    # Session auto-reconnects on next use
    edited_bytes = decode_data_url(f"data:image/png;base64,{result['edited_image']}")
    url, _ = _save_reference_asset(db, character_id, edited_bytes)
    return {
        "ok": True,
        "url": url,
        "cost_usd": result["cost_usd"],
        "edit_type": result.get("edit_result", {}).get("edit_type"),
    }


async def batch_regenerate_references(db: Session) -> dict:
    """Regenerate reference images for ALL characters."""
    characters = db.query(Character).filter(Character.deleted_at.is_(None)).all()
    results = []

    for char in characters:
        try:
            logger.info("[Batch] Regenerating reference for: %s", char.name)
            await regenerate_reference(db, char.id)
            results.append({"id": char.id, "name": char.name, "status": "success"})
        except Exception as e:
            logger.exception("[Batch] Failed for %s: %s", char.name, e)
            results.append(
                {"id": char.id, "name": char.name, "status": "failed", "error": "Reference generation failed"}
            )

    return {"ok": True, "results": results}


async def generate_wizard_preview(db: Session, request: CharacterPreviewRequest) -> dict:
    """Generate temporary preview image(s) for the wizard (no DB save).

    Builds an in-memory Character from tag_ids + loras, composes a
    12-Layer reference prompt, and calls SD WebUI with ControlNet pose.
    """
    from services.generation import generate_scene_image
    from services.prompt.composition import PromptBuilder
    from services.style_context import resolve_style_context_for_profile

    # 1. Validate tag_ids exist
    tags_db: list[Tag] = []
    if request.tag_ids:
        tags_db = db.query(Tag).filter(Tag.id.in_(request.tag_ids)).all()
        found_ids = {t.id for t in tags_db}
        missing = set(request.tag_ids) - found_ids
        if missing:
            raise ValueError(f"Tags not found: {missing}")

    # 2. Build in-memory Character (not persisted)
    temp_char = Character(
        name="__wizard_preview__",
        gender=request.gender,
        loras=[{"lora_id": lr.lora_id, "weight": lr.weight} for lr in (request.loras or [])],
    )
    for tag in tags_db:
        ct = CharacterTag(tag_id=tag.id, weight=1.0, is_permanent=True)
        ct.tag = tag
        temp_char.tags.append(ct)

    # 3. Resolve StyleContext before compose (needed for reference_env_tags/camera_tags + negative)
    style_ctx = resolve_style_context_for_profile(request.style_profile_id, db)

    builder = PromptBuilder(db)
    full_prompt = builder.compose_for_reference(temp_char, style_ctx=style_ctx)
    neg_prompt = _build_reference_negative(style_ctx, None)

    if style_ctx and style_ctx.sd_model_name:
        from services.image_generation_core import _ensure_correct_checkpoint

        await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    steps = style_ctx.default_steps if (style_ctx and style_ctx.default_steps is not None) else SD_REFERENCE_STEPS
    cfg_scale = (
        style_ctx.default_cfg_scale
        if (style_ctx and style_ctx.default_cfg_scale is not None)
        else SD_REFERENCE_CFG_SCALE
    )
    sampler_name = (
        style_ctx.default_sampler_name if (style_ctx and style_ctx.default_sampler_name) else SD_DEFAULT_SAMPLER
    )
    clip_skip = (
        style_ctx.default_clip_skip if (style_ctx and style_ctx.default_clip_skip is not None) else SD_DEFAULT_CLIP_SKIP
    )
    enable_hr = style_ctx.default_enable_hr if (style_ctx and style_ctx.default_enable_hr is not None) else False

    pose = request.controlnet_pose or SD_REFERENCE_CONTROLNET_POSE
    use_cn = bool(pose)
    num_candidates = request.num_candidates

    # Release DB connection before long SD call
    db.close()

    candidates: list[CandidateImage] = []
    for i in range(num_candidates):
        sd_request = SceneGenerateRequest(
            prompt=full_prompt,
            negative_prompt=neg_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler_name=sampler_name,
            clip_skip=clip_skip,
            width=512,
            height=768,
            seed=-1,
            enable_hr=enable_hr,
            hr_scale=1.5 if enable_hr else 1.0,
            hr_upscaler=SD_REFERENCE_HR_UPSCALER,
            denoising_strength=SD_REFERENCE_DENOISING if enable_hr else 0.0,
            use_controlnet=use_cn,
            controlnet_pose=pose if use_cn else None,
            controlnet_weight=SD_REFERENCE_CONTROLNET_WEIGHT,
            controlnet_control_mode=SD_REFERENCE_CONTROLNET_MODE,
        )
        res = await generate_scene_image(sd_request)
        if "image" not in res:
            logger.warning("[WizardPreview] Candidate %d failed, skipping", i + 1)
            continue
        if sd_request.use_controlnet and not res.get("controlnet_pose"):
            logger.warning("[WizardPreview] ControlNet requested but not applied — check SD WebUI ControlNet extension")
        candidates.append(CandidateImage(image=res["image"], seed=res.get("seed", -1)))

    if not candidates:
        raise RuntimeError("Generation failed: no candidates produced")

    return {
        "image": candidates[0].image,
        "used_prompt": full_prompt,
        "seed": candidates[0].seed,
        "candidates": [c.model_dump() for c in candidates],
        "warnings": [],
    }


async def assign_wizard_preview(db: Session, character_id: int, request: AssignPreviewRequest) -> dict:
    """Save a wizard-generated preview image to an existing character."""
    import base64

    _get_character_for_reference(db, character_id, with_tags=False)  # Validates existence + not locked

    # Decode base64
    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image data: {exc}") from exc

    url, asset_id = _save_reference_asset(db, character_id, image_bytes)

    return {
        "reference_image_url": url,
        "asset_id": asset_id,
    }
