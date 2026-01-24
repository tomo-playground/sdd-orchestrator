"""Character CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Character, LoRA, Tag
from schemas import CharacterCreate, CharacterResponse, CharacterUpdate

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=list[CharacterResponse])
async def list_characters(db: Session = Depends(get_db)):
    """List all characters."""
    characters = db.query(Character).order_by(Character.name).all()
    logger.info("📋 [Characters] Listed %d characters", len(characters))
    return characters


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: int, db: Session = Depends(get_db)):
    """Get a single character by ID."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.get("/{character_id}/full")
async def get_character_full(character_id: int, db: Session = Depends(get_db)):
    """Get character with resolved tag names and LoRA info."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Resolve identity tags
    identity_tags = []
    if character.identity_tags:
        tags = db.query(Tag).filter(Tag.id.in_(character.identity_tags)).all()
        identity_tags = [{"id": t.id, "name": t.name, "group_name": t.group_name} for t in tags]

    # Resolve clothing tags
    clothing_tags = []
    if character.clothing_tags:
        tags = db.query(Tag).filter(Tag.id.in_(character.clothing_tags)).all()
        clothing_tags = [{"id": t.id, "name": t.name, "group_name": t.group_name} for t in tags]

    # Resolve LoRA
    lora_info = None
    if character.lora_id:
        lora = db.query(LoRA).filter(LoRA.id == character.lora_id).first()
        if lora:
            lora_info = {
                "id": lora.id,
                "name": lora.name,
                "display_name": lora.display_name,
                "trigger_words": lora.trigger_words,
            }

    return {
        "id": character.id,
        "name": character.name,
        "identity_tags": identity_tags,
        "clothing_tags": clothing_tags,
        "lora": lora_info,
        "lora_weight": float(character.lora_weight) if character.lora_weight else None,
        "preview_image_url": character.preview_image_url,
    }


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    """Create a new character."""
    existing = db.query(Character).filter(Character.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Character already exists")

    character = Character(**data.model_dump())
    db.add(character)
    db.commit()
    db.refresh(character)
    logger.info("✅ [Characters] Created: %s", character.name)
    return character


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(character_id: int, data: CharacterUpdate, db: Session = Depends(get_db)):
    """Update an existing character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)

    db.commit()
    db.refresh(character)
    logger.info("✏️ [Characters] Updated: %s", character.name)
    return character


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
