"""Storyboard creation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.storyboard import Storyboard
from models.scene import Scene
from schemas import StoryboardRequest, StoryboardSave
from services.storyboard import create_storyboard

router = APIRouter(prefix="/storyboards", tags=["storyboard"])


@router.post("/create")
async def create_storyboard_endpoint(request: StoryboardRequest):
    logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return create_storyboard(request)


@router.post("")
async def save_storyboard(request: StoryboardSave, db: Session = Depends(get_db)):
    """Save a full storyboard and its scenes to the DB."""
    logger.info("💾 [Storyboard Save] %s", request.title)
    
    # 1. Create Storyboard
    db_storyboard = Storyboard(
        title=request.title,
        description=request.description,
        default_character_id=request.default_character_id,
        default_style_profile_id=request.default_style_profile_id
    )
    db.add(db_storyboard)
    db.flush() # Get ID
    
    # 2. Create Scenes
    for idx, s_data in enumerate(request.scenes):
        db_scene = Scene(
            storyboard_id=db_storyboard.id,
            order=idx,
            script=s_data.script,
            image_url=s_data.image_url,
            # We can expand this with more fields if needed
        )
        db.add(db_scene)
    
    db.commit()
    db.refresh(db_storyboard)
    return {"status": "success", "storyboard_id": db_storyboard.id}
