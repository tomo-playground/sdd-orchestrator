"""Creative Agent Presets CRUD router."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import CREATIVE_AGENT_CATEGORIES
from database import get_db
from models.creative import CreativeAgentPreset
from schemas_creative import (
    AgentPresetCreate,
    AgentPresetResponse,
    AgentPresetsListResponse,
    AgentPresetUpdate,
    CategoryOption,
    OkResponse,
)

router = APIRouter(prefix="/lab/creative", tags=["creative"])


@router.get("/agent-presets", response_model=AgentPresetsListResponse)
def api_list_presets(category: str | None = None, db: Session = Depends(get_db)):
    """List all active agent presets, optionally filtered by category."""
    query = db.query(CreativeAgentPreset).filter(CreativeAgentPreset.deleted_at.is_(None))
    if category:
        query = query.filter(CreativeAgentPreset.category == category)
    presets = query.order_by(CreativeAgentPreset.id).all()

    from config import BASE_DIR, CREATIVE_AGENT_TEMPLATES

    # Attach template content for informational purposes in UI
    results = []
    for p in presets:
        data = AgentPresetResponse.model_validate(p)
        if p.agent_role and p.agent_role in CREATIVE_AGENT_TEMPLATES:
            tpl_path = BASE_DIR / "templates" / CREATIVE_AGENT_TEMPLATES[p.agent_role]
            if tpl_path.exists():
                try:
                    data.template_content = tpl_path.read_text(encoding="utf-8")
                except Exception:
                    pass
        results.append(data)

    categories = [CategoryOption(**c) for c in CREATIVE_AGENT_CATEGORIES]
    return AgentPresetsListResponse(presets=results, categories=categories)


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

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(preset, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate agent_role or name") from None
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
