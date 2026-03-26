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
    SD_DEFAULT_HEIGHT,
    SD_DEFAULT_SAMPLER,
    SD_DEFAULT_WIDTH,
    SD_HI_RES_SCALE,
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
    asset = asset_service.save_character_reference(character_id, image_bytes)
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
    from services.style_context import resolve_style_context_from_group

    character = _get_character_for_reference(db, character_id, with_tags=True)

    # Resolve StyleContext via Group (needed for reference_env_tags/camera_tags + negative)
    style_ctx = resolve_style_context_from_group(character.group_id, db)

    # ComfyUI: 단순 프롬프트 — weight 강조 없이, 충돌 태그 제거
    import re

    char_tags = character.positive_prompt or ""
    # Strip weight emphasis: (tag:1.3) → tag
    char_tags_clean = re.sub(r"\(([^:()]+):[0-9.]+\)", r"\1", char_tags)
    # Remove abstract/conflicting/unnecessary tags for upper_body reference
    _REMOVE_TAGS = {
        "tall",
        "slim",
        "confident",
        "adult",  # 추상적
        "tote_bag",
        "backpack",
        "bag",  # 소품 (upper_body에 불필요)
        "pleated_skirt",
        "skirt",
        "pants",
        "jeans",
        "shorts",  # 하의 (upper_body에 안 보임)
    }
    tags = [t.strip() for t in char_tags_clean.split(",") if t.strip()]
    # Resolve looking_away vs looking_at_viewer conflict
    has_looking_away = any("looking_away" in t for t in tags)
    filtered = [t for t in tags if t not in _REMOVE_TAGS]
    if has_looking_away:
        filtered = [t for t in filtered if "looking_at_viewer" not in t]
        gaze = ""  # looking_away from character prompt
    else:
        gaze = "looking_at_viewer"
    char_part = ", ".join(filtered)
    gaze_part = f", {gaze}" if gaze else ""
    full_prompt = f"masterpiece, best_quality, {char_part}, solo, upper_body{gaze_part}, simple_background"
    # LoRA 태그 주입 — ComfyUI 클라이언트가 파싱해서 워크플로우 노드로 적용
    if style_ctx and style_ctx.loras:
        for lora in style_ctx.loras:
            lora_name = lora.get("name", "")
            lora_weight = lora.get("weight", 0.7)
            if lora_name:
                full_prompt += f", <lora:{lora_name}:{lora_weight}>"

    # ComfyUI/SDXL: 간결한 negative (중복/weight 제거)
    neg_prompt = (
        "lowres, bad_anatomy, bad_hands, text, error, worst_quality, low_quality, "
        "missing_fingers, extra_digit, extra_fingers, mutated_hands, poorly_drawn_hands, "
        "poorly_drawn_face, deformed, extra_limbs, blurry, watermark, signature, "
        "multiple_views, character_sheet, reference_sheet, "
        "3d, realistic, photorealistic, detailed_background"
    )
    # Merge character-specific negative on top
    if character.negative_prompt:
        existing = {t.strip() for t in neg_prompt.split(",")}
        for tag in character.negative_prompt.split(","):
            tag = tag.strip()
            if tag and tag not in existing:
                neg_prompt += ", " + tag

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
            width=SD_DEFAULT_WIDTH,
            height=SD_DEFAULT_HEIGHT,
            seed=-1,
            enable_hr=enable_hr,
            hr_scale=SD_HI_RES_SCALE if enable_hr else 1.0,
            hr_upscaler=SD_REFERENCE_HR_UPSCALER,
            denoising_strength=SD_REFERENCE_DENOISING if enable_hr else 0.0,
            use_controlnet=use_cn,
            controlnet_pose=pose if use_cn else None,
            controlnet_weight=SD_REFERENCE_CONTROLNET_WEIGHT,
            controlnet_control_mode=SD_REFERENCE_CONTROLNET_MODE,
            comfy_workflow="reference",
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
            width=SD_DEFAULT_WIDTH,
            height=SD_DEFAULT_HEIGHT,
            seed=-1,
            enable_hr=enable_hr,
            hr_scale=SD_HI_RES_SCALE if enable_hr else 1.0,
            hr_upscaler=SD_REFERENCE_HR_UPSCALER,
            denoising_strength=SD_REFERENCE_DENOISING if enable_hr else 0.0,
            use_controlnet=use_cn,
            controlnet_pose=pose if use_cn else None,
            controlnet_weight=SD_REFERENCE_CONTROLNET_WEIGHT,
            controlnet_control_mode=SD_REFERENCE_CONTROLNET_MODE,
            comfy_workflow="reference",
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
