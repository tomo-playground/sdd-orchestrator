"""Character CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import (
    DEFAULT_REFERENCE_BASE_PROMPT,
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    logger,
)
from database import get_db
from models import Character, LoRA, Tag
from pydantic import BaseModel
from schemas import CharacterCreate, CharacterResponse, CharacterUpdate
from services.controlnet import generate_reference_for_character
from services.prompt_composition import get_effective_mode

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

    # Resolve multiple LoRAs
    loras_info = []
    loras_db: list[LoRA] = []
    if character.loras:
        lora_ids = [item["lora_id"] for item in character.loras]
        loras_db = db.query(LoRA).filter(LoRA.id.in_(lora_ids)).all()
        lora_map = {lora.id: lora for lora in loras_db}

        for item in character.loras:
            lora = lora_map.get(item["lora_id"])
            if lora:
                # Use optimal_weight if calibrated, otherwise use preset weight
                effective_weight = (
                    float(lora.optimal_weight)
                    if lora.optimal_weight is not None
                    else item.get("weight", 1.0)
                )
                loras_info.append({
                    "id": lora.id,
                    "name": lora.name,
                    "display_name": lora.display_name,
                    "trigger_words": lora.trigger_words,
                    "weight": effective_weight,
                    "optimal_weight": float(lora.optimal_weight) if lora.optimal_weight else None,
                    "calibration_score": float(lora.calibration_score) if lora.calibration_score else None,
                    "lora_type": lora.lora_type,
                })

    # Determine effective prompt mode
    effective_mode = get_effective_mode(character, loras_db)

    return {
        "id": character.id,
        "name": character.name,
        "description": character.description,
        "gender": character.gender,
        "identity_tags": identity_tags,
        "clothing_tags": clothing_tags,
        "loras": loras_info,
        "recommended_negative": character.recommended_negative or [],
        "custom_base_prompt": character.custom_base_prompt,
        "custom_negative_prompt": character.custom_negative_prompt,
        "preview_image_url": character.preview_image_url,
        "prompt_mode": character.prompt_mode,
        "ip_adapter_weight": character.ip_adapter_weight,
        "ip_adapter_model": character.ip_adapter_model,
        "effective_mode": effective_mode,
    }


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    """Create a new character."""
    existing = db.query(Character).filter(Character.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Character already exists")

    # Convert loras list to JSONB-compatible format
    char_data = data.model_dump()
    if char_data.get("loras"):
        char_data["loras"] = [{"lora_id": lora["lora_id"], "weight": lora["weight"]} for lora in char_data["loras"]]

    # Set default reference prompts if not provided
    if not char_data.get("reference_base_prompt"):
        char_data["reference_base_prompt"] = DEFAULT_REFERENCE_BASE_PROMPT
    if not char_data.get("reference_negative_prompt"):
        char_data["reference_negative_prompt"] = DEFAULT_REFERENCE_NEGATIVE_PROMPT

    character = Character(**char_data)
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


@router.post("/{character_id}/regenerate-reference")
async def regenerate_reference(character_id: int, db: Session = Depends(get_db)):
    """Regenerate the IP-Adapter reference image for this character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    try:
        filename = await generate_reference_for_character(db, character)

        # Update preview_image_url with cache busting
        import time
        base_url = f"/assets/references/{filename}"
        new_url = f"{base_url}?t={int(time.time())}"

        # Store base URL without query params in DB
        if character.preview_image_url != base_url:
            character.preview_image_url = base_url
            db.commit()
            db.refresh(character)

        return {"ok": True, "filename": filename, "preview_image_url": new_url}
    except Exception as e:
        logger.exception("Failed to regenerate reference for %s", character.name)
        raise HTTPException(status_code=500, detail=str(e))


class SuggestTagsRequest(BaseModel):
    """Request body for tag suggestion endpoint."""
    prompt: str


class SuggestedTag(BaseModel):
    """Suggested tag with metadata."""
    id: int
    name: str
    group_name: str | None


class SuggestTagsResponse(BaseModel):
    """Response body for tag suggestion endpoint."""
    identity_tags: list[SuggestedTag]
    clothing_tags: list[SuggestedTag]


@router.post("/suggest-tags", response_model=SuggestTagsResponse)
async def suggest_tags(data: SuggestTagsRequest, db: Session = Depends(get_db)):
    """Suggest tags based on Base Prompt input.

    Parses the prompt, matches against DB tags, and returns suggestions
    grouped by category (identity vs clothing).
    """
    # 1. Parse prompt (comma-separated)
    tokens = [token.strip() for token in data.prompt.split(",") if token.strip()]

    # 2. Normalize tokens (handle both formats: "brown hair" and "brown_hair")
    normalized_tokens = []
    for token in tokens:
        normalized_tokens.append(token.replace(" ", "_"))
        if "_" in token:
            normalized_tokens.append(token.replace("_", " "))

    # 3. Query DB for matching tags
    matched_tags = db.query(Tag).filter(Tag.name.in_(normalized_tokens)).all()

    # 4. Group by category
    identity_tags = []
    clothing_tags = []

    for tag in matched_tags:
        suggested_tag = SuggestedTag(
            id=tag.id,
            name=tag.name,
            group_name=tag.group_name
        )

        if tag.category == "identity":
            identity_tags.append(suggested_tag)
        elif tag.category == "clothing":
            clothing_tags.append(suggested_tag)

    logger.info(
        "🏷️ [Tag Suggestion] Prompt tokens: %d, Matched: %d (identity: %d, clothing: %d)",
        len(tokens),
        len(matched_tags),
        len(identity_tags),
        len(clothing_tags)
    )

    return SuggestTagsResponse(
        identity_tags=identity_tags,
        clothing_tags=clothing_tags
    )
