"""Project CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.group import Group
from models.project import Project
from models.sd_model import StyleProfile
from schemas import (
    DeleteStatusResponse,
    EffectiveConfigResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    QuickStartRequest,
    QuickStartResponse,
)
from services.config_resolver import apply_system_defaults, resolve_effective_config

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@router.post("/quick-start", response_model=QuickStartResponse, status_code=201)
def quick_start(body: QuickStartRequest, db: Session = Depends(get_db)):
    """Create Project + Group + default StyleProfile in one transaction."""
    project = Project(name=body.project_name)
    db.add(project)
    db.flush()

    default_style = db.query(StyleProfile).filter(StyleProfile.is_default.is_(True)).first()
    style_id = default_style.id if default_style else None

    group = Group(
        project_id=project.id,
        name=body.group_name,
        style_profile_id=style_id,
    )
    db.add(group)
    db.commit()
    db.refresh(project)
    db.refresh(group)

    return QuickStartResponse(
        project_id=project.id,
        group_id=group.id,
        style_profile_id=style_id,
        message="Quick start completed",
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).options(joinedload(Project.groups)).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**body.model_dump(exclude_unset=True))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/effective-config", response_model=EffectiveConfigResponse)
def get_project_effective_config(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = resolve_effective_config(project)
    apply_system_defaults(result, db)
    return EffectiveConfigResponse(
        render_preset_id=result["values"].get("render_preset_id"),
        style_profile_id=result["values"].get("style_profile_id"),
        sources=result["sources"],
    )


@router.delete("/{project_id}", response_model=DeleteStatusResponse)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        db.delete(project)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete project with existing groups") from None
    db.commit()
    return {"status": "deleted", "id": project_id}
