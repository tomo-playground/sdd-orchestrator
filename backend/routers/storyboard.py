"""Storyboard CRUD endpoints (thin router delegating to service layer)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Storyboard
from schemas import StoryboardRequest, StoryboardSave, StoryboardUpdate
from services.storyboard import (
    create_storyboard,
    delete_storyboard_from_db,
    get_storyboard_by_id,
    list_storyboards_from_db,
    permanent_delete_storyboard,
    save_storyboard_to_db,
    update_storyboard_in_db,
    update_storyboard_metadata,
)

router = APIRouter(prefix="/storyboards", tags=["storyboard"])


@router.post("/create")
async def create_storyboard_endpoint(request: StoryboardRequest, db: Session = Depends(get_db)):
    logger.info("\U0001f4e5 [Storyboard Req] %s", request.model_dump())
    return await create_storyboard(request, db)


@router.post("")
async def save_storyboard(request: StoryboardSave, db: Session = Depends(get_db)):
    return save_storyboard_to_db(db, request)


@router.get("/trash")
def list_trashed_storyboards(db: Session = Depends(get_db)):
    """List soft-deleted storyboards."""
    items = db.query(Storyboard).filter(
        Storyboard.deleted_at.isnot(None),
    ).order_by(Storyboard.deleted_at.desc()).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None,
        }
        for s in items
    ]


@router.get("")
def list_storyboards(group_id: int | None = None, project_id: int | None = None, db: Session = Depends(get_db)):
    return list_storyboards_from_db(db, group_id=group_id, project_id=project_id)


@router.get("/{storyboard_id}")
def get_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    return get_storyboard_by_id(db, storyboard_id)


@router.put("/{storyboard_id}")
async def update_storyboard(
    storyboard_id: int, request: StoryboardSave, db: Session = Depends(get_db)
):
    return update_storyboard_in_db(db, storyboard_id, request)


@router.patch("/{storyboard_id}/metadata")
async def patch_storyboard_metadata(
    storyboard_id: int, request: StoryboardUpdate, db: Session = Depends(get_db)
):
    """Partially update storyboard metadata (title, caption, etc)."""
    return update_storyboard_metadata(db, storyboard_id, request)


@router.delete("/{storyboard_id}")
async def delete_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    return delete_storyboard_from_db(db, storyboard_id)


@router.post("/{storyboard_id}/restore")
async def restore_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted storyboard."""
    storyboard = db.query(Storyboard).filter(
        Storyboard.id == storyboard_id,
        Storyboard.deleted_at.isnot(None),
    ).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Trashed storyboard not found")
    storyboard.deleted_at = None
    db.commit()
    logger.info("[Storyboard Restore] id=%d title=%s", storyboard_id, storyboard.title)
    return {"ok": True, "restored": storyboard.title}


@router.delete("/{storyboard_id}/permanent")
async def permanently_delete_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    """Permanently delete a storyboard and all associated assets."""
    return permanent_delete_storyboard(db, storyboard_id)
