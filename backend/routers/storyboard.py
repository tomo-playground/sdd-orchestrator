"""Storyboard CRUD endpoints (thin router delegating to service layer)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from schemas import StoryboardRequest, StoryboardSave
from services.storyboard import (
    create_storyboard,
    delete_storyboard_from_db,
    get_storyboard_by_id,
    list_storyboards_from_db,
    save_storyboard_to_db,
    update_storyboard_in_db,
)

router = APIRouter(prefix="/storyboards", tags=["storyboard"])


@router.post("/create")
async def create_storyboard_endpoint(request: StoryboardRequest):
    logger.info("\U0001f4e5 [Storyboard Req] %s", request.model_dump())
    return await create_storyboard(request)


@router.post("")
async def save_storyboard(request: StoryboardSave, db: Session = Depends(get_db)):
    return save_storyboard_to_db(db, request)


@router.get("")
def list_storyboards(db: Session = Depends(get_db)):
    return list_storyboards_from_db(db)


@router.get("/{storyboard_id}")
def get_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    return get_storyboard_by_id(db, storyboard_id)


@router.put("/{storyboard_id}")
async def update_storyboard(
    storyboard_id: int, request: StoryboardSave, db: Session = Depends(get_db)
):
    return update_storyboard_in_db(db, storyboard_id, request)


@router.delete("/{storyboard_id}")
async def delete_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    return delete_storyboard_from_db(db, storyboard_id)
