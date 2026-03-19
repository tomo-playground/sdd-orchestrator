"""Group CRUD endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.character import Character
from models.group import Group
from models.project import Project
from models.storyboard import Storyboard
from schemas import (
    DeleteStatusResponse,
    EffectiveConfigResponse,
    GroupCreate,
    GroupDefaultsResponse,
    GroupResponse,
    GroupTrashItem,
    GroupUpdate,
    RenderPresetResponse,
    StatusResponse,
)
from services.config_resolver import (
    apply_system_defaults,
    resolve_effective_config,
)

router = APIRouter(prefix="/groups", tags=["groups"])
admin_router = APIRouter(prefix="/groups", tags=["groups-admin"])

_GROUP_RESPONSE_OPTIONS = (
    joinedload(Group.style_profile),
    joinedload(Group.narrator_voice_preset),
)


def _attach_character_counts(db: Session, groups: list[Group]) -> list[Group]:
    """Batch-load active character counts onto Group instances."""
    counts = dict(
        db.query(Character.group_id, func.count(Character.id))
        .filter(Character.deleted_at.is_(None))
        .group_by(Character.group_id)
        .all()
    )
    for g in groups:
        g._character_count = counts.get(g.id, 0)  # type: ignore[attr-defined]
    return groups


@router.get("/trash", response_model=list[GroupTrashItem])
def list_deleted_groups(db: Session = Depends(get_db)):
    """List soft-deleted groups for trash view."""
    groups = db.query(Group).filter(Group.deleted_at.isnot(None)).order_by(Group.deleted_at.desc()).all()
    return groups


@router.get("", response_model=list[GroupResponse])
def list_groups(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Group).options(*_GROUP_RESPONSE_OPTIONS).filter(Group.deleted_at.is_(None))
    if project_id is not None:
        query = query.filter(Group.project_id == project_id)
    return _attach_character_counts(db, query.all())


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = (
        db.query(Group)
        .options(*_GROUP_RESPONSE_OPTIONS)
        .filter(Group.id == group_id, Group.deleted_at.is_(None))
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    _attach_character_counts(db, [group])
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
    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.is_(None)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    db.commit()
    return db.query(Group).options(*_GROUP_RESPONSE_OPTIONS).filter(Group.id == group_id).first()


# ---- Group Defaults ----


@router.get("/{group_id}/defaults", response_model=GroupDefaultsResponse)
def get_group_defaults(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.is_(None)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    from services.groups.defaults import infer_group_defaults

    return infer_group_defaults(group_id, db)


# ---- Effective Config ----


@router.get("/{group_id}/effective-config", response_model=EffectiveConfigResponse)
def get_group_effective_config(group_id: int, db: Session = Depends(get_db)):
    from models.render_preset import RenderPreset

    group = (
        db.query(Group)
        .options(joinedload(Group.project))
        .filter(Group.id == group_id, Group.deleted_at.is_(None))
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
        style_profile_id=result["values"].get("style_profile_id"),
        narrator_voice_preset_id=result["values"].get("narrator_voice_preset_id"),
        sources=result["sources"],
    )


# ---- Soft Delete / Restore ----


@router.delete("/{group_id}", response_model=DeleteStatusResponse)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.is_(None)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Block if active (non-soft-deleted) storyboards exist
    active_count = (
        db.query(Storyboard)
        .filter(
            Storyboard.group_id == group_id,
            Storyboard.deleted_at.is_(None),
        )
        .count()
    )
    if active_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Group has {active_count} active storyboard(s)",
        )

    now = datetime.now(UTC)
    group.deleted_at = now

    # Cascade soft-delete: characters
    db.query(Character).filter(
        Character.group_id == group_id,
        Character.deleted_at.is_(None),
    ).update({Character.deleted_at: now}, synchronize_session=False)

    # NOTE: already soft-deleted storyboards keep their original deleted_at
    # (they were individually deleted before the group, so restore should not affect them)

    db.commit()
    return {"status": "deleted", "id": group_id}


@router.post("/{group_id}/restore", response_model=StatusResponse)
def restore_group(group_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted group and its cascade-deleted characters."""
    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.isnot(None)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Deleted group not found")

    batch_ts = group.deleted_at
    group.deleted_at = None

    # Restore characters deleted in the same batch
    db.query(Character).filter(
        Character.group_id == group_id,
        Character.deleted_at == batch_ts,
    ).update({Character.deleted_at: None}, synchronize_session=False)

    db.commit()
    return {"status": "restored", "id": group_id}


# ---- Admin: Permanent Delete ----


@admin_router.delete("/{group_id}/permanent", response_model=StatusResponse)
def permanent_delete_group(group_id: int, db: Session = Depends(get_db)):
    """Permanently delete a soft-deleted group and all associated data."""
    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.isnot(None)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Deleted group not found")

    # Bulk delete: relies on DB-level CASCADE for child tables
    # (character_tags, storyboard_characters, scenes, etc.)
    db.query(Character).filter(Character.group_id == group_id).delete(synchronize_session=False)
    db.query(Storyboard).filter(Storyboard.group_id == group_id).delete(synchronize_session=False)

    db.delete(group)
    db.commit()
    return {"status": "permanently_deleted", "id": group_id}
