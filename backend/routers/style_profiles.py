"""Style Profile CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Embedding, LoRA, SDModel, StyleProfile
from schemas import StyleProfileCreate, StyleProfileResponse, StyleProfileUpdate

router = APIRouter(prefix="/style-profiles", tags=["style-profiles"])


@router.get("", response_model=list[StyleProfileResponse])
async def list_style_profiles(active_only: bool = True, db: Session = Depends(get_db)):
    """List all style profiles."""
    query = db.query(StyleProfile)
    if active_only:
        query = query.filter(StyleProfile.is_active)
    profiles = query.order_by(StyleProfile.name).all()
    logger.info("📋 [StyleProfiles] Listed %d profiles", len(profiles))
    return profiles


@router.get("/default")
async def get_default_profile(db: Session = Depends(get_db)):
    """Get the default style profile with full details."""
    profile = db.query(StyleProfile).filter(StyleProfile.is_default).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No default profile set")
    return _build_full_profile(db, profile)


@router.get("/{profile_id}", response_model=StyleProfileResponse)
async def get_style_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get a single style profile."""
    profile = db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    return profile


@router.get("/{profile_id}/full")
async def get_style_profile_full(profile_id: int, db: Session = Depends(get_db)):
    """Get style profile with all resolved references."""
    profile = db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    return _build_full_profile(db, profile)


def _build_full_profile(db: Session, profile: StyleProfile) -> dict:
    """Build full profile with resolved SD model, LoRAs, embeddings."""
    # Resolve SD model
    sd_model = None
    if profile.sd_model_id:
        model = db.query(SDModel).filter(SDModel.id == profile.sd_model_id).first()
        if model:
            sd_model = {"id": model.id, "name": model.name, "display_name": model.display_name}

    # Resolve LoRAs
    loras = []
    if profile.loras:
        for lora_config in profile.loras:
            lora = db.query(LoRA).filter(LoRA.id == lora_config.get("lora_id")).first()
            if lora:
                loras.append({
                    "id": lora.id,
                    "name": lora.name,
                    "display_name": lora.display_name,
                    "trigger_words": lora.trigger_words,
                    "weight": lora_config.get("weight", 1.0),
                })

    # Resolve negative embeddings
    negative_embeddings = []
    if profile.negative_embeddings:
        embs = db.query(Embedding).filter(Embedding.id.in_(profile.negative_embeddings)).all()
        negative_embeddings = [{"id": e.id, "name": e.name, "trigger_word": e.trigger_word} for e in embs]

    # Resolve positive embeddings
    positive_embeddings = []
    if profile.positive_embeddings:
        embs = db.query(Embedding).filter(Embedding.id.in_(profile.positive_embeddings)).all()
        positive_embeddings = [{"id": e.id, "name": e.name, "trigger_word": e.trigger_word} for e in embs]

    return {
        "id": profile.id,
        "name": profile.name,
        "display_name": profile.display_name,
        "description": profile.description,
        "sd_model": sd_model,
        "loras": loras,
        "negative_embeddings": negative_embeddings,
        "positive_embeddings": positive_embeddings,
        "default_positive": profile.default_positive,
        "default_negative": profile.default_negative,
        "is_default": profile.is_default,
        "is_active": profile.is_active,
    }


@router.post("", response_model=StyleProfileResponse, status_code=201)
async def create_style_profile(data: StyleProfileCreate, db: Session = Depends(get_db)):
    """Create a new style profile."""
    existing = db.query(StyleProfile).filter(StyleProfile.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Style profile already exists")

    # Convert LoRAWeight to dict for JSONB
    profile_data = data.model_dump()
    if profile_data.get("loras"):
        profile_data["loras"] = [lw if isinstance(lw, dict) else lw.model_dump() for lw in profile_data["loras"]]

    # If this is set as default, unset other defaults
    if data.is_default:
        db.query(StyleProfile).filter(StyleProfile.is_default).update({"is_default": False})

    profile = StyleProfile(**profile_data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    logger.info("✅ [StyleProfiles] Created: %s", profile.name)
    return profile


@router.put("/{profile_id}", response_model=StyleProfileResponse)
async def update_style_profile(profile_id: int, data: StyleProfileUpdate, db: Session = Depends(get_db)):
    """Update a style profile."""
    profile = db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")

    update_data = data.model_dump(exclude_unset=True)

    # Convert LoRAWeight to dict for JSONB
    if "loras" in update_data and update_data["loras"]:
        update_data["loras"] = [lw if isinstance(lw, dict) else lw.model_dump() for lw in update_data["loras"]]

    # If setting as default, unset other defaults
    if update_data.get("is_default"):
        db.query(StyleProfile).filter(StyleProfile.is_default, StyleProfile.id != profile_id).update(
            {"is_default": False}
        )

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    logger.info("✏️ [StyleProfiles] Updated: %s", profile.name)
    return profile


@router.delete("/{profile_id}")
async def delete_style_profile(profile_id: int, db: Session = Depends(get_db)):
    """Delete a style profile."""
    profile = db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")

    name = profile.name
    db.delete(profile)
    db.commit()
    logger.info("🗑️ [StyleProfiles] Deleted: %s", name)
    return {"ok": True, "deleted": name}
