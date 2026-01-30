"""Storyboard CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from config import logger
from database import get_db
from models.associations import SceneCharacterAction, SceneTag
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import StoryboardRequest, StoryboardSave
from services.storyboard import create_storyboard

router = APIRouter(prefix="/storyboards", tags=["storyboard"])


def _create_scenes(db: Session, storyboard_id: int, scenes_data: list) -> None:
    """Create scenes with tags and character actions for a storyboard."""
    for idx, s_data in enumerate(scenes_data):
        db_scene = Scene(
            storyboard_id=storyboard_id,
            order=idx,
            script=s_data.script,
            speaker=s_data.speaker,
            duration=s_data.duration,
            description=s_data.description,
            image_prompt=s_data.image_prompt,
            image_prompt_ko=s_data.image_prompt_ko,
            negative_prompt=s_data.negative_prompt,
            image_url=s_data.image_url,
            width=s_data.width,
            height=s_data.height,
            steps=s_data.steps,
            cfg_scale=s_data.cfg_scale,
            sampler_name=s_data.sampler_name,
            seed=s_data.seed,
            clip_skip=s_data.clip_skip,
            context_tags=s_data.context_tags,
        )
        db.add(db_scene)
        db.flush()

        if s_data.tags:
            for t_data in s_data.tags:
                db.add(SceneTag(scene_id=db_scene.id, tag_id=t_data.tag_id, weight=t_data.weight))

        if s_data.character_actions:
            for a_data in s_data.character_actions:
                db.add(SceneCharacterAction(
                    scene_id=db_scene.id,
                    character_id=a_data.character_id,
                    tag_id=a_data.tag_id,
                    weight=a_data.weight,
                ))


def _serialize_scene(scene: Scene) -> dict:
    """Serialize a Scene ORM object to dict for API response."""
    return {
        "scene_id": scene.order,
        "script": scene.script,
        "speaker": scene.speaker,
        "duration": scene.duration,
        "description": scene.description,
        "image_prompt": scene.image_prompt,
        "image_prompt_ko": scene.image_prompt_ko,
        "negative_prompt": scene.negative_prompt,
        "image_url": scene.image_url,
        "width": scene.width,
        "height": scene.height,
        "steps": scene.steps,
        "cfg_scale": scene.cfg_scale,
        "sampler_name": scene.sampler_name,
        "seed": scene.seed,
        "clip_skip": scene.clip_skip,
        "context_tags": scene.context_tags,
        "tags": [{"tag_id": t.tag_id, "weight": t.weight} for t in scene.tags],
        "character_actions": [
            {"character_id": a.character_id, "tag_id": a.tag_id, "weight": a.weight}
            for a in scene.character_actions
        ],
    }


@router.post("/create")
async def create_storyboard_endpoint(request: StoryboardRequest):
    logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return create_storyboard(request)


@router.post("")
async def save_storyboard(request: StoryboardSave, db: Session = Depends(get_db)):
    """Save a full storyboard and its scenes to the DB."""
    logger.info("💾 [Storyboard Save] %s", request.title)

    db_storyboard = Storyboard(
        title=request.title,
        description=request.description,
        default_character_id=request.default_character_id,
        default_style_profile_id=request.default_style_profile_id,
    )
    db.add(db_storyboard)
    db.flush()

    _create_scenes(db, db_storyboard.id, request.scenes)

    db.commit()
    db.refresh(db_storyboard)
    return {"status": "success", "storyboard_id": db_storyboard.id}


@router.get("")
def list_storyboards(db: Session = Depends(get_db)):
    """List all storyboards with scene/image counts."""
    storyboards = db.query(Storyboard).options(joinedload(Storyboard.scenes)).all()

    result = []
    for s in storyboards:
        scenes = s.scenes or []
        result.append({
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "scene_count": len(scenes),
            "image_count": sum(1 for sc in scenes if sc.image_url),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return result


@router.get("/{storyboard_id}")
def get_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    """Get a storyboard with all scenes, tags, and character actions."""
    storyboard = (
        db.query(Storyboard)
        .options(
            joinedload(Storyboard.scenes).joinedload(Scene.tags),
            joinedload(Storyboard.scenes).joinedload(Scene.character_actions),
        )
        .filter(Storyboard.id == storyboard_id)
        .first()
    )

    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    scenes = sorted(storyboard.scenes, key=lambda s: s.order)

    return {
        "id": storyboard.id,
        "title": storyboard.title,
        "description": storyboard.description,
        "default_character_id": storyboard.default_character_id,
        "default_style_profile_id": storyboard.default_style_profile_id,
        "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
        "updated_at": storyboard.updated_at.isoformat() if storyboard.updated_at else None,
        "scenes": [_serialize_scene(sc) for sc in scenes],
    }


@router.put("/{storyboard_id}")
async def update_storyboard(
    storyboard_id: int, request: StoryboardSave, db: Session = Depends(get_db)
):
    """Update a storyboard by replacing all scenes."""
    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("✏️ [Storyboard Update] id=%d title=%s", storyboard_id, request.title)

    # Update metadata
    storyboard.title = request.title
    storyboard.description = request.description
    storyboard.default_character_id = request.default_character_id
    storyboard.default_style_profile_id = request.default_style_profile_id

    # Delete existing scenes (CASCADE removes tags & actions)
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id).delete()
    db.flush()

    # Recreate scenes
    _create_scenes(db, storyboard_id, request.scenes)

    db.commit()
    db.refresh(storyboard)
    return {"status": "success", "storyboard_id": storyboard.id}


@router.delete("/{storyboard_id}")
async def delete_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    """Delete a storyboard and all its scenes (CASCADE)."""
    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("🗑️ [Storyboard Delete] id=%d title=%s", storyboard_id, storyboard.title)

    db.delete(storyboard)
    db.commit()
    return {"status": "success"}
