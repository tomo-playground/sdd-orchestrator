"""Character CRUD endpoints for Pure V3."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from config import (
    DEFAULT_REFERENCE_BASE_PROMPT,
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    logger,
)
from database import get_db
from models import Character, LoRA, Tag, CharacterTag
from schemas import CharacterCreate, CharacterResponse, CharacterUpdate

router = APIRouter(prefix="/characters", tags=["characters"])

@router.get("", response_model=list[CharacterResponse])
async def list_characters(db: Session = Depends(get_db)):
    """List all characters with their tags and tag metadata."""
    characters = db.query(Character).options(
        joinedload(Character.tags).joinedload(CharacterTag.tag)
    ).order_by(Character.name).all()
    
    # Pre-fetch all LoRAs to avoid N+1
    all_loras = db.query(LoRA).all()
    lora_map = {l.id: l for l in all_loras}

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
    character = db.query(Character).options(
        joinedload(Character.tags).joinedload(CharacterTag.tag)
    ).filter(Character.id == character_id).first()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
        
    for char_tag in character.tags:
        char_tag.name = char_tag.tag.name
        char_tag.layer = char_tag.tag.default_layer
        
    if character.loras:
        # Enrich LoRA data
        lora_ids = [l.get("lora_id") for l in character.loras if l.get("lora_id")]
        if lora_ids:
            lora_objs = db.query(LoRA).filter(LoRA.id.in_(lora_ids)).all()
            lora_map = {l.id: l for l in lora_objs}
            
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
    existing = db.query(Character).filter(Character.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Character already exists")

    char_data = data.model_dump(exclude={"tags"})
    
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

    if data.tags:
        for tag_link in data.tags:
            link = CharacterTag(
                character_id=character.id,
                tag_id=tag_link.tag_id,
                weight=tag_link.weight,
                is_permanent=tag_link.is_permanent
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

    update_data = data.model_dump(exclude={"tags"}, exclude_unset=True)
    
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

    if data.tags is not None:
        db.query(CharacterTag).filter(CharacterTag.character_id == character_id).delete()
        for tag_link in data.tags:
            link = CharacterTag(
                character_id=character_id,
                tag_id=tag_link.tag_id,
                weight=tag_link.weight,
                is_permanent=tag_link.is_permanent
            )
            db.add(link)

    db.commit()
    return await get_character(character_id, db)

@router.delete("/{character_id}")
async def delete_character(character_id: int, db: Session = Depends(get_db)):
    """Delete a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    name = character.name
    db.delete(character)
    db.commit()
    logger.info("🗑️ [Characters] Deleted: %s", name)
    return {"ok": True, "deleted": name}

@router.get("/{character_id}/full", response_model=CharacterResponse)
async def get_character_full(character_id: int, db: Session = Depends(get_db)):
    """Alias for get_character to maintain frontend compatibility."""
    return await get_character(character_id, db)

@router.post("/{character_id}/regenerate-reference")
async def regenerate_reference(character_id: int, db: Session = Depends(get_db)):
    """Regenerate the character's reference image using its tags and reference prompts."""
    from services.generation import generate_scene_image
    from schemas import SceneGenerateRequest, ImageStoreRequest
    from .scene import store_scene_image
    import base64

    character = db.query(Character).options(
        joinedload(Character.tags).joinedload(CharacterTag.tag)
    ).filter(Character.id == character_id).first()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build prompt from reference_base_prompt + character tags + LoRAs
    tag_names = [t.tag.name for t in character.tags]
    base = character.reference_base_prompt or ""
    
    # Include LoRAs
    lora_tags = []
    if character.loras:
        for lora_info in character.loras:
            lora_id = lora_info.get("lora_id")
            weight = lora_info.get("weight", 0.7)
            lora_obj = db.query(LoRA).filter(LoRA.id == lora_id).first()
            if lora_obj:
                lora_tags.append(f"<lora:{lora_obj.name}:{weight}>")
                if lora_obj.trigger_words:
                    tag_names.extend(lora_obj.trigger_words)

    full_prompt_raw = f"{base}, {', '.join(tag_names)}, {', '.join(lora_tags)}" if base else f"{', '.join(tag_names)}, {', '.join(lora_tags)}"
    
    # Normalize to Danbooru standard
    from services.prompt.prompt import normalize_and_fix_tags
    full_prompt = normalize_and_fix_tags(full_prompt_raw)
    
    # Generate image
    request = SceneGenerateRequest(
        prompt=full_prompt,
        negative_prompt=character.reference_negative_prompt or "",
        steps=25,
        cfg_scale=7.5,
        width=512,
        height=768,
        seed=-1
    )
    
    res = await generate_scene_image(request)
    if "image" not in res:
        raise HTTPException(status_code=500, detail="Generation failed")

    # Store image
    image_b64 = f"data:image/png;base64,{res['image']}"
    store_res = await store_scene_image(ImageStoreRequest(image_b64=image_b64))
    
    # Update character
    character.preview_image_url = store_res["url"]
    db.commit()
    
    return {"ok": True, "url": character.preview_image_url}
