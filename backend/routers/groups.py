"""Group CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.group import Group
from models.group_config import GroupConfig
from models.project import Project
from models.storyboard import Storyboard
from schemas import (
    EffectiveConfigResponse,
    GroupConfigResponse,
    GroupConfigUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    RenderPresetResponse,
)
from services.config_resolver import (
    SD_SYSTEM_DEFAULTS,
    apply_system_defaults,
    resolve_effective_config,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse])
def list_groups(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Group)
    if project_id is not None:
        query = query.filter(Group.project_id == project_id)
    return query.all()


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    group = Group(
        project_id=body.project_id,
        name=body.name,
        description=body.description,
    )
    db.add(group)
    db.flush()

    # Pre-fill GroupConfig with project defaults + system defaults
    config_fields: dict = {}
    for field in ("render_preset_id", "style_profile_id", "character_id"):
        val = getattr(body, field, None) or getattr(project, field, None)
        if val is not None:
            config_fields[field] = val

    # System default: style_profile with is_default=true
    if "style_profile_id" not in config_fields:
        from models import StyleProfile

        default_profile = db.query(StyleProfile.id).filter(
            StyleProfile.is_default.is_(True)
        ).first()
        if default_profile:
            config_fields["style_profile_id"] = default_profile.id

    # System defaults: SD generation settings
    for field, default_val in SD_SYSTEM_DEFAULTS.items():
        config_fields.setdefault(field, default_val)

    config = GroupConfig(group_id=group.id, **config_fields)
    db.add(config)
    db.commit()
    db.refresh(group)
    return group


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(group_id: int, body: GroupUpdate, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


# ---- Group Config (1:1) ----


@router.get("/{group_id}/config", response_model=GroupConfigResponse)
def get_group_config(group_id: int, db: Session = Depends(get_db)):
    """Return group config, creating one if it does not exist yet."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    config = _get_or_create_config(group, db)
    return config


@router.put("/{group_id}/config", response_model=GroupConfigResponse)
def update_group_config(
    group_id: int,
    data: GroupConfigUpdate,
    db: Session = Depends(get_db),
):
    """Update group config fields (partial update via exclude_unset)."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    config = _get_or_create_config(group, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


def _get_or_create_config(group: Group, db: Session) -> GroupConfig:
    """Return existing GroupConfig or create a new empty one."""
    config = db.query(GroupConfig).filter(GroupConfig.group_id == group.id).first()
    if config is None:
        config = GroupConfig(group_id=group.id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


# ---- Effective Config ----


@router.get("/{group_id}/effective-config", response_model=EffectiveConfigResponse)
def get_group_effective_config(group_id: int, db: Session = Depends(get_db)):
    from models.render_preset import RenderPreset

    group = (
        db.query(Group)
        .options(joinedload(Group.config), joinedload(Group.project))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    result = resolve_effective_config(group.project, group)
    apply_system_defaults(result, db)

    # Load full render_preset if ID exists
    render_preset_id = result["values"].get("render_preset_id")
    render_preset = None
    if render_preset_id:
        preset_obj = db.query(RenderPreset).filter(RenderPreset.id == render_preset_id).first()
        if preset_obj:
            render_preset = RenderPresetResponse.model_validate(preset_obj)

    return EffectiveConfigResponse(
        render_preset_id=render_preset_id,
        render_preset=render_preset,
        character_id=result["values"].get("character_id"),
        style_profile_id=result["values"].get("style_profile_id"),
        narrator_voice_preset_id=result["values"].get("narrator_voice_preset_id"),
        language=result["values"].get("language"),
        structure=result["values"].get("structure"),
        duration=result["values"].get("duration"),
        sd_steps=result["values"].get("sd_steps"),
        sd_cfg_scale=result["values"].get("sd_cfg_scale"),
        sd_sampler_name=result["values"].get("sd_sampler_name"),
        sd_clip_skip=result["values"].get("sd_clip_skip"),
        sources=result["sources"],
    )


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Block if active (non-soft-deleted) storyboards exist
    active_count = (
        db.query(Storyboard)
        .filter(Storyboard.group_id == group_id, Storyboard.deleted_at.is_(None))
        .count()
    )
    if active_count > 0:
        raise HTTPException(status_code=409, detail="Cannot delete group with existing storyboards")

    # Hard-delete any soft-deleted storyboards (use ORM delete for cascade)
    soft_deleted = (
        db.query(Storyboard)
        .filter(Storyboard.group_id == group_id, Storyboard.deleted_at.isnot(None))
        .all()
    )
    for sb in soft_deleted:
        db.delete(sb)

    db.delete(group)
    db.commit()
    return {"status": "deleted", "id": group_id}
