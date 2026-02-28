"""Group CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.group import Group
from models.project import Project
from models.storyboard import Storyboard
from schemas import (
    EffectiveConfigResponse,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    RenderPresetResponse,
)
from services.config_resolver import (
    apply_system_defaults,
    resolve_effective_config,
)

router = APIRouter(prefix="/groups", tags=["groups"])

_GROUP_RESPONSE_OPTIONS = (
    joinedload(Group.style_profile),
    joinedload(Group.narrator_voice_preset),
)


@router.get("", response_model=list[GroupResponse])
def list_groups(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Group).options(*_GROUP_RESPONSE_OPTIONS)
    if project_id is not None:
        query = query.filter(Group.project_id == project_id)
    return query.all()


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).options(*_GROUP_RESPONSE_OPTIONS).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    fields: dict = {
        "project_id": body.project_id,
        "name": body.name,
        "description": body.description,
    }

    # Config fields
    for field in ("render_preset_id", "style_profile_id", "narrator_voice_preset_id"):
        val = getattr(body, field, None) or getattr(project, field, None)
        if val is not None:
            fields[field] = val

    if body.channel_dna is not None:
        fields["channel_dna"] = body.channel_dna.model_dump()

    # System default: style_profile with is_default=true
    if "style_profile_id" not in fields:
        from models import StyleProfile

        default_profile = db.query(StyleProfile.id).filter(StyleProfile.is_default.is_(True)).first()
        if default_profile:
            fields["style_profile_id"] = default_profile.id

    group = Group(**fields)
    db.add(group)
    db.commit()
    return db.query(Group).options(*_GROUP_RESPONSE_OPTIONS).filter(Group.id == group.id).first()


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(group_id: int, body: GroupUpdate, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "channel_dna" and value is not None:
            setattr(group, key, value if isinstance(value, dict) else value.model_dump())
        else:
            setattr(group, key, value)
    db.commit()
    return db.query(Group).options(*_GROUP_RESPONSE_OPTIONS).filter(Group.id == group_id).first()


# ---- Effective Config ----


@router.get("/{group_id}/effective-config", response_model=EffectiveConfigResponse)
def get_group_effective_config(group_id: int, db: Session = Depends(get_db)):
    from models.render_preset import RenderPreset

    group = db.query(Group).options(joinedload(Group.project)).filter(Group.id == group_id).first()
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
        style_profile_id=result["values"].get("style_profile_id"),
        narrator_voice_preset_id=result["values"].get("narrator_voice_preset_id"),
        channel_dna=result.get("channel_dna"),
        sources=result["sources"],
    )


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Block if active (non-soft-deleted) storyboards exist
    active_count = db.query(Storyboard).filter(Storyboard.group_id == group_id, Storyboard.deleted_at.is_(None)).count()
    if active_count > 0:
        raise HTTPException(status_code=409, detail="Cannot delete group with existing storyboards")

    # Hard-delete any soft-deleted storyboards (use ORM delete for cascade)
    soft_deleted = db.query(Storyboard).filter(Storyboard.group_id == group_id, Storyboard.deleted_at.isnot(None)).all()
    for sb in soft_deleted:
        db.delete(sb)

    db.delete(group)
    db.commit()
    return {"status": "deleted", "id": group_id}
