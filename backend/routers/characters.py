"""Character CRUD endpoints for Pure V3."""

from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from config import (
    DEFAULT_REFERENCE_BASE_PROMPT,
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    SD_REFERENCE_CFG_SCALE,
    SD_REFERENCE_DENOISING,
    SD_REFERENCE_HR_UPSCALER,
    SD_REFERENCE_STEPS,
    logger,
)
from database import get_db
from models import Character, CharacterTag, LoRA
from schemas import CharacterCreate, CharacterResponse, CharacterUpdate

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("/trash")
async def list_trashed_characters(db: Session = Depends(get_db)):
    """List soft-deleted characters."""
    items = (
        db.query(Character)
        .filter(
            Character.deleted_at.isnot(None),
        )
        .order_by(Character.deleted_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
        }
        for c in items
    ]


@router.get("", response_model=list[CharacterResponse])
async def list_characters(project_id: int | None = None, db: Session = Depends(get_db)):
    """List all characters with their tags and tag metadata."""
    query = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.deleted_at.is_(None))
    )
    if project_id is not None:
        query = query.filter(Character.project_id == project_id)
    characters = query.order_by(Character.name).all()

    # Pre-fetch all LoRAs to avoid N+1
    all_loras = db.query(LoRA).all()
    lora_map = {lora.id: lora for lora in all_loras}

    # Map tag metadata and enrich LoRAs
    for char in characters:
        for char_tag in char.tags:
            char_tag.name = char_tag.tag.name
            char_tag.layer = char_tag.tag.default_layer

        if char.loras:
            # Enrich LoRA data
            enriched = []
            for l_data in char.loras:
                # Ensure we have a dict copy to modify
                l_new = l_data.copy()
                lid = l_new.get("lora_id")
                if lid and lid in lora_map:
                    lora = lora_map[lid]
                    l_new["name"] = lora.name
                    l_new["trigger_words"] = lora.trigger_words
                    l_new["lora_type"] = lora.lora_type
                enriched.append(l_new)
            char.loras = enriched

    return characters


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: int, db: Session = Depends(get_db)):
    """Get a single character by ID with tag metadata."""
    character = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == character_id, Character.deleted_at.is_(None))
        .first()
    )

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    for char_tag in character.tags:
        char_tag.name = char_tag.tag.name
        char_tag.layer = char_tag.tag.default_layer

    if character.loras:
        # Enrich LoRA data
        lora_ids = [lora_item.get("lora_id") for lora_item in character.loras if lora_item.get("lora_id")]
        if lora_ids:
            lora_objs = db.query(LoRA).filter(LoRA.id.in_(lora_ids)).all()
            lora_map = {lora_obj.id: lora_obj for lora_obj in lora_objs}

            enriched = []
            for l_data in character.loras:
                l_new = l_data.copy()
                lid = l_new.get("lora_id")
                if lid and lid in lora_map:
                    lora = lora_map[lid]
                    l_new["name"] = lora.name
                    l_new["trigger_words"] = lora.trigger_words
                    l_new["lora_type"] = lora.lora_type
                enriched.append(l_new)
            character.loras = enriched

    return character


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    """Create a new character and link tags."""
    existing = (
        db.query(Character)
        .filter(
            Character.name == data.name,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Character name already exists")

    char_data = data.model_dump(exclude={"tags", "identity_tags", "clothing_tags"})

    # Enrich LoRA data before saving (Denormalization)
    if char_data.get("loras"):
        enriched_loras = []
        for l_item in char_data["loras"]:
            lid = l_item.get("lora_id")
            if lid:
                lora_obj = db.query(LoRA).filter(LoRA.id == lid).first()
                if lora_obj:
                    l_item["name"] = lora_obj.name
                    l_item["trigger_words"] = lora_obj.trigger_words
                    l_item["lora_type"] = lora_obj.lora_type
            enriched_loras.append(l_item)
        char_data["loras"] = enriched_loras

    if not char_data.get("reference_base_prompt"):
        char_data["reference_base_prompt"] = DEFAULT_REFERENCE_BASE_PROMPT
    if not char_data.get("reference_negative_prompt"):
        char_data["reference_negative_prompt"] = DEFAULT_REFERENCE_NEGATIVE_PROMPT

    character = Character(**char_data)
    db.add(character)
    db.flush()

    # V3 Tag Integration: Merge normalized 'tags' with legacy identity/clothing tags
    final_tags = []
    if data.tags:
        final_tags.extend(data.tags)

    # Legacy Fallback: Convert legacy id lists to CharacterTagLink objects
    if data.identity_tags:
        from schemas import CharacterTagLink

        for tid in data.identity_tags:
            if not any(t.tag_id == tid for t in final_tags):
                final_tags.append(CharacterTagLink(tag_id=tid, is_permanent=True))

    if data.clothing_tags:
        from schemas import CharacterTagLink

        for tid in data.clothing_tags:
            if not any(t.tag_id == tid for t in final_tags):
                final_tags.append(CharacterTagLink(tag_id=tid, is_permanent=False))

    if final_tags:
        for tag_link in final_tags:
            link = CharacterTag(
                character_id=character.id,
                tag_id=tag_link.tag_id,
                weight=tag_link.weight,
                is_permanent=tag_link.is_permanent,
            )
            db.add(link)

    db.commit()
    return await get_character(character.id, db)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(character_id: int, data: CharacterUpdate, db: Session = Depends(get_db)):
    """Update an existing character and sync tags."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = data.model_dump(exclude={"tags", "identity_tags", "clothing_tags"}, exclude_unset=True)

    # Enrich LoRA data if being updated
    if "loras" in update_data and update_data["loras"]:
        enriched_loras = []
        for l_item in update_data["loras"]:
            lid = l_item.get("lora_id")
            if lid:
                lora_obj = db.query(LoRA).filter(LoRA.id == lid).first()
                if lora_obj:
                    l_item["name"] = lora_obj.name
                    l_item["trigger_words"] = lora_obj.trigger_words
                    l_item["lora_type"] = lora_obj.lora_type
            enriched_loras.append(l_item)
        update_data["loras"] = enriched_loras

    for key, value in update_data.items():
        setattr(character, key, value)

    if data.tags is not None or data.identity_tags is not None or data.clothing_tags is not None:
        db.query(CharacterTag).filter(CharacterTag.character_id == character_id).delete()

        # Merge tags from all sources (V3 'tags' vs Legacy 'identity/clothing_tags')
        final_tags = []
        if data.tags:
            final_tags.extend(data.tags)

        if data.identity_tags:
            from schemas import CharacterTagLink

            for tid in data.identity_tags:
                if not any(t.tag_id == tid for t in final_tags):
                    final_tags.append(CharacterTagLink(tag_id=tid, is_permanent=True))

        if data.clothing_tags:
            from schemas import CharacterTagLink

            for tid in data.clothing_tags:
                if not any(t.tag_id == tid for t in final_tags):
                    final_tags.append(CharacterTagLink(tag_id=tid, is_permanent=False))

        for tag_link in final_tags:
            link = CharacterTag(
                character_id=character_id,
                tag_id=tag_link.tag_id,
                weight=tag_link.weight,
                is_permanent=tag_link.is_permanent,
            )
            db.add(link)

    db.commit()
    return await get_character(character_id, db)


@router.delete("/{character_id}")
async def delete_character(character_id: int, db: Session = Depends(get_db)):
    """Soft-delete a character."""
    character = (
        db.query(Character)
        .filter(
            Character.id == character_id,
            Character.deleted_at.is_(None),
        )
        .first()
    )
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character.deleted_at = datetime.now(UTC)
    db.commit()
    logger.info("[Characters] Soft deleted: %s", character.name)
    return {"ok": True, "deleted": character.name}


@router.post("/{character_id}/restore")
async def restore_character(character_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted character."""
    character = (
        db.query(Character)
        .filter(
            Character.id == character_id,
            Character.deleted_at.isnot(None),
        )
        .first()
    )
    if not character:
        raise HTTPException(status_code=404, detail="Trashed character not found")
    character.deleted_at = None
    db.commit()
    logger.info("[Characters] Restored: %s", character.name)
    return {"ok": True, "restored": character.name}


@router.delete("/{character_id}/permanent")
async def permanently_delete_character(character_id: int, db: Session = Depends(get_db)):
    """Permanently delete a character and cleanup IP-Adapter references."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    name = character.name
    try:
        from services.controlnet import delete_reference_image

        delete_reference_image(name)
    except Exception as e:
        logger.warning("[Characters] Failed to delete reference image for %s: %s", name, e)

    db.delete(character)
    db.commit()
    logger.info("[Characters] Permanently deleted: %s", name)
    return {"ok": True, "deleted": name}


@router.get("/{character_id}/full", response_model=CharacterResponse)
async def get_character_full(character_id: int, db: Session = Depends(get_db)):
    """Alias for get_character to maintain frontend compatibility."""
    return await get_character(character_id, db)


@router.post("/{character_id}/regenerate-reference")
async def regenerate_reference(character_id: int, db: Session = Depends(get_db)):
    """Regenerate the character's reference image using its tags and reference prompts."""

    from schemas import SceneGenerateRequest
    from services.generation import generate_scene_image

    character = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == character_id, Character.deleted_at.is_(None))
        .first()
    )

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if character.preview_locked:
        raise HTTPException(status_code=400, detail="Preview image is locked")

    # Build prompt from reference_base_prompt + character tags + LoRAs
    tag_names = [t.tag.name for t in character.tags]
    base = character.reference_base_prompt or ""

    # Include LoRAs (scale down character LoRAs for reference: face identity only)
    lora_tags = []
    if character.loras:
        for lora_info in character.loras:
            lora_id = lora_info.get("lora_id")
            weight = lora_info.get("weight", 0.7)
            lora_obj = db.query(LoRA).filter(LoRA.id == lora_id).first()
            if lora_obj:
                if lora_obj.lora_type == "style":
                    ref_weight = weight
                else:
                    ref_weight = round(weight * 0.25, 2)
                lora_tags.append(f"<lora:{lora_obj.name}:{ref_weight}>")
                if lora_obj.trigger_words:
                    tag_names.extend(lora_obj.trigger_words)

    full_prompt_raw = (
        f"{base}, {', '.join(tag_names)}, {', '.join(lora_tags)}"
        if base
        else f"{', '.join(tag_names)}, {', '.join(lora_tags)}"
    )

    from services.prompt.prompt import normalize_and_fix_tags

    full_prompt = normalize_and_fix_tags(full_prompt_raw)
    neg_prompt = character.reference_negative_prompt or ""

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
        raise HTTPException(status_code=500, detail="Generation failed")

    # Session auto-reconnects on next use
    from services.asset_service import AssetService
    from services.image import decode_data_url

    image_bytes = decode_data_url(f"data:image/png;base64,{res['image']}")
    asset_service = AssetService(db)
    asset = asset_service.save_character_preview(character_id, image_bytes)

    db.query(Character).filter(Character.id == character_id).update({"preview_image_asset_id": asset.id})
    db.commit()

    return {"ok": True, "url": asset.url}


@router.post("/{character_id}/enhance-preview")
async def enhance_preview(character_id: int, db: Session = Depends(get_db)):
    """Enhance the character's preview image using Gemini image generation."""
    from services.asset_service import AssetService
    from services.image import decode_data_url, load_as_data_url
    from services.imagen_edit import get_imagen_service

    character = db.query(Character).filter(Character.id == character_id, Character.deleted_at.is_(None)).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if character.preview_locked:
        raise HTTPException(status_code=400, detail="Preview image is locked")

    if not character.preview_image_url:
        raise HTTPException(status_code=400, detail="No preview image to enhance")

    image_b64 = load_as_data_url(character.preview_image_url)

    # Release DB connection before long Gemini API call
    db.close()

    service = get_imagen_service()
    result = await service.enhance_image(image_b64)

    # Session auto-reconnects on next use
    enhanced_bytes = decode_data_url(f"data:image/png;base64,{result['enhanced_image']}")
    asset_service = AssetService(db)
    asset = asset_service.save_character_preview(character_id, enhanced_bytes)

    db.query(Character).filter(Character.id == character_id).update({"preview_image_asset_id": asset.id})
    db.commit()

    return {"ok": True, "url": asset.url, "cost_usd": result["cost_usd"]}


@router.post("/{character_id}/edit-preview")
async def edit_preview(
    character_id: int,
    instruction: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Edit the character's preview image with a natural language instruction via Gemini."""
    from services.asset_service import AssetService
    from services.image import decode_data_url, load_as_data_url
    from services.imagen_edit import get_imagen_service

    character = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == character_id, Character.deleted_at.is_(None))
        .first()
    )
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if character.preview_locked:
        raise HTTPException(status_code=400, detail="Preview image is locked")

    if not character.preview_image_url:
        raise HTTPException(status_code=400, detail="No preview image to edit")

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
    asset_service = AssetService(db)
    asset = asset_service.save_character_preview(character_id, edited_bytes)

    db.query(Character).filter(Character.id == character_id).update({"preview_image_asset_id": asset.id})
    db.commit()

    return {
        "ok": True,
        "url": asset.url,
        "cost_usd": result["cost_usd"],
        "edit_type": result.get("edit_result", {}).get("edit_type"),
    }


@router.post("/batch-regenerate-references")
async def batch_regenerate_references(db: Session = Depends(get_db)):
    """Regenerate reference images for ALL characters using latest Hires. fix settings."""
    characters = db.query(Character).filter(Character.deleted_at.is_(None)).all()
    results = []

    for char in characters:
        try:
            logger.info("🔄 [Batch] Regenerating reference for: %s", char.name)
            # Call the same logic as regenerate_reference
            await regenerate_reference(char.id, db)
            results.append({"id": char.id, "name": char.name, "status": "success"})
        except Exception as e:
            logger.error("❌ [Batch] Failed for %s: %s", char.name, e)
            results.append({"id": char.id, "name": char.name, "status": "failed", "error": str(e)})

    return {"ok": True, "results": results}
