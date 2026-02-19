"""Character preview image generation, enhancement, and editing.

All functions are async — they call external APIs (SD WebUI, Gemini Imagen)
that may take 30-60s.

db.close() pattern: SQLAlchemy Session.close() returns the connection to the
pool. On the next query the Session transparently acquires a new connection.
We close before long external calls to avoid holding a DB connection idle.
"""

from sqlalchemy.orm import Session, joinedload

from config import (
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    SD_REFERENCE_CFG_SCALE,
    SD_REFERENCE_DENOISING,
    SD_REFERENCE_HR_UPSCALER,
    SD_REFERENCE_STEPS,
    logger,
)
from models import Character, CharacterTag, Tag
from schemas import AssignPreviewRequest, CharacterPreviewRequest, SceneGenerateRequest


def _resolve_quality_tags_for_character(character: Character, db: Session) -> list[str] | None:
    """Resolve StyleProfile quality tags via Character's most recent Storyboard → Group.

    Path: Character → StoryboardCharacter → Storyboard → Group → Config → StyleProfile.
    Returns parsed default_positive tokens, or None if no StyleProfile is configured.
    """
    from models.storyboard import Storyboard
    from models.storyboard_character import StoryboardCharacter
    from services.prompt import split_prompt_tokens
    from services.style_context import resolve_style_context_from_group

    # Find the most recent storyboard using this character
    sc = (
        db.query(StoryboardCharacter)
        .join(Storyboard, StoryboardCharacter.storyboard_id == Storyboard.id)
        .filter(
            StoryboardCharacter.character_id == character.id,
            Storyboard.deleted_at.is_(None),
        )
        .order_by(Storyboard.id.desc())
        .first()
    )
    if not sc:
        return None

    storyboard = db.query(Storyboard).filter(Storyboard.id == sc.storyboard_id).first()
    if not storyboard or not storyboard.group_id:
        return None

    ctx = resolve_style_context_from_group(storyboard.group_id, db)
    if not ctx or not ctx.default_positive:
        return None

    return split_prompt_tokens(ctx.default_positive)


def _get_character_for_preview(db: Session, character_id: int, *, with_tags: bool = False) -> Character:
    """Fetch character with validation for preview operations."""
    query = db.query(Character)
    if with_tags:
        query = query.options(joinedload(Character.tags).joinedload(CharacterTag.tag))
    character = query.filter(Character.id == character_id, Character.deleted_at.is_(None)).first()
    if not character:
        raise ValueError("Character not found")
    if character.preview_locked:
        raise ValueError("Preview image is locked")
    return character


def _save_preview_asset(db: Session, character_id: int, image_bytes: bytes) -> tuple[str, int]:
    """Save image bytes as a preview asset and update the character. Returns (url, asset_id)."""
    from services.asset_service import AssetService

    asset_service = AssetService(db)
    asset = asset_service.save_character_preview(character_id, image_bytes)
    db.query(Character).filter(Character.id == character_id).update({"preview_image_asset_id": asset.id})
    db.commit()
    return asset.url, asset.id


async def regenerate_reference(db: Session, character_id: int) -> dict:
    """Regenerate the character's reference image using V3 12-Layer prompt system."""
    from services.generation import generate_scene_image
    from services.image import decode_data_url
    from services.prompt.v3_composition import V3PromptBuilder

    character = _get_character_for_preview(db, character_id, with_tags=True)

    # Resolve StyleProfile quality tags (Group → Config → StyleProfile.default_positive)
    quality_tags = _resolve_quality_tags_for_character(character, db)

    builder = V3PromptBuilder(db)
    full_prompt = builder.compose_for_reference(character, quality_tags=quality_tags)
    neg_prompt = character.reference_negative_prompt or DEFAULT_REFERENCE_NEGATIVE_PROMPT
    if character.recommended_negative:
        extras = [n for n in character.recommended_negative if n not in neg_prompt]
        if extras:
            neg_prompt += ", " + ", ".join(extras)

    # Release DB connection before long SD WebUI call (~30-60s)
    db.close()

    request = SceneGenerateRequest(
        prompt=full_prompt,
        negative_prompt=neg_prompt,
        steps=SD_REFERENCE_STEPS,
        cfg_scale=SD_REFERENCE_CFG_SCALE,
        width=512,
        height=768,
        seed=-1,
        enable_hr=True,
        hr_scale=1.5,
        hr_upscaler=SD_REFERENCE_HR_UPSCALER,
        denoising_strength=SD_REFERENCE_DENOISING,
    )

    res = await generate_scene_image(request)
    if "image" not in res:
        raise RuntimeError("Generation failed")

    # Session auto-reconnects on next use
    image_bytes = decode_data_url(f"data:image/png;base64,{res['image']}")
    url, _ = _save_preview_asset(db, character_id, image_bytes)
    return {"ok": True, "url": url}


async def enhance_preview(db: Session, character_id: int) -> dict:
    """Enhance the character's preview image using Gemini Imagen."""
    from services.image import decode_data_url, load_as_data_url
    from services.imagen_edit import get_imagen_service

    character = _get_character_for_preview(db, character_id)
    if not character.preview_image_url:
        raise ValueError("No preview image to enhance")

    image_b64 = load_as_data_url(character.preview_image_url)

    # Release DB connection before long Gemini API call
    db.close()

    service = get_imagen_service()
    result = await service.enhance_image(image_b64)

    # Session auto-reconnects on next use
    enhanced_bytes = decode_data_url(f"data:image/png;base64,{result['enhanced_image']}")
    url, _ = _save_preview_asset(db, character_id, enhanced_bytes)
    return {"ok": True, "url": url, "cost_usd": result["cost_usd"]}


async def edit_preview(db: Session, character_id: int, instruction: str) -> dict:
    """Edit the character's preview image with a natural language instruction via Gemini."""
    from services.image import decode_data_url, load_as_data_url
    from services.imagen_edit import get_imagen_service

    character = _get_character_for_preview(db, character_id, with_tags=True)
    if not character.preview_image_url:
        raise ValueError("No preview image to edit")

    image_b64 = load_as_data_url(character.preview_image_url)
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
    url, _ = _save_preview_asset(db, character_id, edited_bytes)
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
            logger.error("[Batch] Failed for %s: %s", char.name, e)
            results.append({"id": char.id, "name": char.name, "status": "failed", "error": str(e)})

    return {"ok": True, "results": results}


async def generate_wizard_preview(db: Session, request: CharacterPreviewRequest) -> dict:
    """Generate a temporary preview image for the wizard (no DB save).

    Builds an in-memory Character from tag_ids + loras, composes a
    V3 12-Layer reference prompt, and calls SD WebUI.
    """
    from services.generation import generate_scene_image
    from services.prompt.v3_composition import V3PromptBuilder

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
    # Attach tag associations in-memory
    for tag in tags_db:
        ct = CharacterTag(tag_id=tag.id, weight=1.0, is_permanent=True)
        ct.tag = tag  # Populate relationship for V3PromptBuilder
        temp_char.tags.append(ct)

    # 3. Compose prompt
    builder = V3PromptBuilder(db)
    full_prompt = builder.compose_for_reference(temp_char)
    neg_prompt = DEFAULT_REFERENCE_NEGATIVE_PROMPT

    # Release DB connection before long SD call
    db.close()

    sd_request = SceneGenerateRequest(
        prompt=full_prompt,
        negative_prompt=neg_prompt,
        steps=SD_REFERENCE_STEPS,
        cfg_scale=SD_REFERENCE_CFG_SCALE,
        width=512,
        height=768,
        seed=-1,
        enable_hr=True,
        hr_scale=1.5,
        hr_upscaler=SD_REFERENCE_HR_UPSCALER,
        denoising_strength=SD_REFERENCE_DENOISING,
    )

    res = await generate_scene_image(sd_request)
    if "image" not in res:
        raise RuntimeError("Generation failed: no image in response")

    return {
        "image": res["image"],
        "used_prompt": full_prompt,
        "seed": res.get("info", {}).get("seed", -1) if isinstance(res.get("info"), dict) else -1,
        "warnings": res.get("warnings", []),
    }


async def assign_wizard_preview(db: Session, character_id: int, request: AssignPreviewRequest) -> dict:
    """Save a wizard-generated preview image to an existing character."""
    import base64

    _get_character_for_preview(db, character_id, with_tags=False)  # Validates existence + not locked

    # Decode base64
    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image data: {exc}") from exc

    url, asset_id = _save_preview_asset(db, character_id, image_bytes)

    return {
        "preview_image_url": url,
        "asset_id": asset_id,
    }
