"""Group CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.group import Group
from schemas import EffectiveConfigResponse, GroupCreate, GroupResponse, GroupUpdate
from services.config_resolver import resolve_effective_config

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


@router.get("/{group_id}/effective-config", response_model=EffectiveConfigResponse)
def get_group_effective_config(group_id: int, db: Session = Depends(get_db)):
    group = (
        db.query(Group)
        .options(joinedload(Group.render_preset), joinedload(Group.project))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    result = resolve_effective_config(group.project, group)
    # Resolve the actual render_preset object from whichever level provided the id
    preset = group.render_preset or getattr(group.project, "render_preset", None)
    return EffectiveConfigResponse(
        render_preset_id=result["values"].get("render_preset_id"),
        default_character_id=result["values"].get("default_character_id"),
        default_style_profile_id=result["values"].get("default_style_profile_id"),
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
        raise HTTPException(status_code=409, detail="Cannot delete group with existing storyboards")
    db.commit()
    return {"status": "deleted", "id": group_id}
