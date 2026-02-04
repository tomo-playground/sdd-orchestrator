"""Group CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.group import Group
from models.group_config import GroupConfig
from schemas import (
    EffectiveConfigResponse,
    GroupConfigResponse,
    GroupConfigUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
)
from services.config_resolver import apply_system_defaults, resolve_effective_config

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse])
def list_groups(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Group).options(joinedload(Group.render_preset))
    if project_id is not None:
        query = query.filter(Group.project_id == project_id)
    return query.all()


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).options(joinedload(Group.render_preset)).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db)):
    group = Group(**body.model_dump(exclude_unset=True))
    db.add(group)
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
    group = (
        db.query(Group)
        .options(joinedload(Group.config), joinedload(Group.render_preset), joinedload(Group.project))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    result = resolve_effective_config(group.project, group)
    apply_system_defaults(result, db)
    # Resolve render_preset from group_config or project
    preset = None
    if group.config and group.config.render_preset:
        preset = group.config.render_preset
    if preset is None:
        preset = group.render_preset or getattr(group.project, "render_preset", None)
    return EffectiveConfigResponse(
        render_preset_id=result["values"].get("render_preset_id"),
        default_character_id=result["values"].get("default_character_id"),
        default_style_profile_id=result["values"].get("default_style_profile_id"),
        narrator_voice_preset_id=result["values"].get("narrator_voice_preset_id"),
        language=result["values"].get("language"),
        structure=result["values"].get("structure"),
        duration=result["values"].get("duration"),
        render_preset=preset,
        sources=result["sources"],
    )


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    try:
        db.delete(group)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete group with existing storyboards") from None
    db.commit()
    return {"status": "deleted", "id": group_id}
