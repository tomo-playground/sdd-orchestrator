"""RenderPreset CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.group import Group
from models.render_preset import RenderPreset
from schemas import RenderPresetCreate, RenderPresetResponse, RenderPresetUpdate, StatusResponse

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


# Schema→ORM field name mapping (DB column names are kept unchanged)
_PRESET_FIELD_MAP = {"is_audio_ducking_enabled": "audio_ducking"}


@admin_router.post("", response_model=RenderPresetResponse, status_code=201)
def create_render_preset(body: RenderPresetCreate, db: Session = Depends(get_db)):
    data = {_PRESET_FIELD_MAP.get(k, k): v for k, v in body.model_dump(exclude_unset=True).items()}
    preset = RenderPreset(**data, is_system=False)
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
        col = _PRESET_FIELD_MAP.get(key, key)
        setattr(preset, col, value)
    db.commit()
    db.refresh(preset)
    return preset


@admin_router.delete("/{preset_id}", response_model=StatusResponse)
def delete_render_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(RenderPreset).filter(RenderPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Render preset not found")

    # FK reference check: active groups using this preset
    ref_count = (
        db.query(Group)
        .filter(
            Group.render_preset_id == preset_id,
            Group.deleted_at.is_(None),
        )
        .count()
    )
    if ref_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Render preset is used by {ref_count} active group(s)",
        )

    db.delete(preset)
    db.commit()
    return {"status": "deleted", "id": preset_id}
