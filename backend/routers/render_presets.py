"""RenderPreset CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.render_preset import RenderPreset
from schemas import RenderPresetCreate, RenderPresetResponse, RenderPresetUpdate

service_router = APIRouter(prefix="/render-presets", tags=["render-presets"])
admin_router = APIRouter(prefix="/render-presets", tags=["render-presets-admin"])


@service_router.get("", response_model=list[RenderPresetResponse])
def list_render_presets(db: Session = Depends(get_db)):
    return db.query(RenderPreset).order_by(RenderPreset.id).all()


@service_router.get("/{preset_id}", response_model=RenderPresetResponse)
def get_render_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(RenderPreset).filter(RenderPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Render preset not found")
    return preset


@admin_router.post("", response_model=RenderPresetResponse, status_code=201)
def create_render_preset(body: RenderPresetCreate, db: Session = Depends(get_db)):
    preset = RenderPreset(**body.model_dump(exclude_unset=True), is_system=False)
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@admin_router.put("/{preset_id}", response_model=RenderPresetResponse)
def update_render_preset(
    preset_id: int,
    body: RenderPresetUpdate,
    db: Session = Depends(get_db),
):
    preset = db.query(RenderPreset).filter(RenderPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Render preset not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(preset, key, value)
    db.commit()
    db.refresh(preset)
    return preset


@admin_router.delete("/{preset_id}")
def delete_render_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(RenderPreset).filter(RenderPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Render preset not found")
    db.delete(preset)
    db.commit()
    return {"status": "deleted", "id": preset_id}
