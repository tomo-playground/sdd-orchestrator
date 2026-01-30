"""Storyboard creation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.associations import SceneCharacterAction, SceneTag
from models.scene import Scene
from models.storyboard import Storyboard
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
            description=s_data.description,
            image_url=s_data.image_url,
            width=s_data.width,
            height=s_data.height,
        )
        db.add(db_scene)
        db.flush() # Get Scene ID

        # 3. Save Scene Tags (Ambient/Environment)
        if s_data.tags:
            for t_data in s_data.tags:
                s_tag = SceneTag(
                    scene_id=db_scene.id,
                    tag_id=t_data.tag_id,
                    weight=t_data.weight
                )
                db.add(s_tag)

        # 4. Save Scene Character Actions
        if s_data.character_actions:
            for a_data in s_data.character_actions:
                s_action = SceneCharacterAction(
                    scene_id=db_scene.id,
                    character_id=a_data.character_id,
                    tag_id=a_data.tag_id,
                    weight=a_data.weight
                )
                db.add(s_action)

    db.commit()
    db.refresh(db_storyboard)
    return {"status": "success", "storyboard_id": db_storyboard.id}


@router.get("")
def list_storyboards(db: Session = Depends(get_db)):
    """List all storyboards."""
    storyboards = db.query(Storyboard).all()
    
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in storyboards
    ]
