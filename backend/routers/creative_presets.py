"""Creative Agent Presets CRUD router."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.creative import CreativeAgentPreset
from schemas_creative import (
    AgentPresetCreate,
    AgentPresetResponse,
    AgentPresetUpdate,
    OkResponse,
)

router = APIRouter(prefix="/lab/creative", tags=["creative"])


@router.get("/agent-presets", response_model=list[AgentPresetResponse])
def api_list_presets(db: Session = Depends(get_db)):
    """List all active agent presets."""
    return (
        db.query(CreativeAgentPreset)
        .filter(CreativeAgentPreset.deleted_at.is_(None))
        .order_by(CreativeAgentPreset.id)
        .all()
    )


@router.post("/agent-presets", response_model=AgentPresetResponse)
def api_create_preset(
    req: AgentPresetCreate,
    db: Session = Depends(get_db),
):
    """Create a new agent preset."""
    preset = CreativeAgentPreset(**req.model_dump())
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.put("/agent-presets/{preset_id}", response_model=AgentPresetResponse)
def api_update_preset(
    preset_id: int,
    req: AgentPresetUpdate,
    db: Session = Depends(get_db),
):
    """Update an agent preset."""
    preset = db.get(CreativeAgentPreset, preset_id)
    if not preset or preset.deleted_at:
        raise HTTPException(status_code=404, detail="Preset not found")
    if preset.is_system:
        raise HTTPException(status_code=400, detail="Cannot edit system presets")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(preset, field, value)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/agent-presets/{preset_id}", response_model=OkResponse)
def api_delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete an agent preset."""
    preset = db.get(CreativeAgentPreset, preset_id)
    if not preset or preset.deleted_at:
        raise HTTPException(status_code=404, detail="Preset not found")
    if preset.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system presets")

    preset.deleted_at = datetime.now(UTC)
    db.commit()
    return {"ok": True}
