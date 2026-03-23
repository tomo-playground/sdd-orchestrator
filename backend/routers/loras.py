"""LoRA CRUD endpoints.

Service API: GET (read-only list + detail)
Admin API: CUD
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import LoRA
from schemas import (
    LoRACreate,
    LoRAResponse,
    LoRAUpdate,
    OkDeletedResponse,
)

service_router = APIRouter(prefix="/loras", tags=["loras"])
admin_router = APIRouter(prefix="/loras", tags=["loras-admin"])


@service_router.get("", response_model=list[LoRAResponse])
async def list_loras(
    lora_type: str | None = Query(None, description="Filter by lora_type (style, character)"),
    base_model: str | None = Query(None, description="Filter by base_model (SD1.5, SDXL)"),
    db: Session = Depends(get_db),
):
    """List all LoRAs with optional filters."""
    query = db.query(LoRA).filter(LoRA.is_active.is_(True))
    if lora_type:
        query = query.filter(LoRA.lora_type == lora_type)
    if base_model:
        query = query.filter(LoRA.base_model == base_model)
    loras = query.order_by(LoRA.name).all()
    logger.info("📋 [LoRAs] Listed %d loras", len(loras))
    return loras


@service_router.get("/{lora_id}", response_model=LoRAResponse)
async def get_lora(lora_id: int, db: Session = Depends(get_db)):
    """Get a single LoRA by ID."""
    lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA not found")
    return lora


@admin_router.post("", response_model=LoRAResponse, status_code=201)
async def create_lora(data: LoRACreate, db: Session = Depends(get_db)):
    """Create a new LoRA."""
    existing = db.query(LoRA).filter(LoRA.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="LoRA already exists")

    lora = LoRA(**data.model_dump())
    db.add(lora)
    db.commit()
    db.refresh(lora)
    logger.info("✅ [LoRAs] Created: %s", lora.name)
    return lora


@admin_router.put("/{lora_id}", response_model=LoRAResponse)
async def update_lora(lora_id: int, data: LoRAUpdate, db: Session = Depends(get_db)):
    """Update an existing LoRA."""
    lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA not found")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(lora, key, value)

    db.commit()
    db.refresh(lora)
    logger.info("✏️ [LoRAs] Updated: %s", lora.name)

    return lora


@admin_router.delete("/{lora_id}", response_model=OkDeletedResponse)
async def delete_lora(lora_id: int, db: Session = Depends(get_db)):
    """Delete a LoRA."""
    lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA not found")

    name = lora.name
    db.delete(lora)
    db.commit()
    logger.info("🗑️ [LoRAs] Deleted: %s", name)
    return {"ok": True, "deleted": name}
