"""Storyboard CRUD endpoints."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from config import logger
from database import get_db
from models.associations import SceneCharacterAction, SceneTag
from models.media_asset import MediaAsset
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import StoryboardRequest, StoryboardSave
from services.storyboard import create_storyboard

router = APIRouter(prefix="/storyboards", tags=["storyboard"])


def _create_scenes(db: Session, storyboard_id: int, scenes_data: list) -> None:
    """Create scenes with tags and character actions for a storyboard."""
    for idx, s_data in enumerate(scenes_data):
        # Filter out base64 data URLs (they exceed VARCHAR(500) limit)
        image_url = s_data.image_url
        if image_url and image_url.startswith("data:"):
            image_url = None

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
            width=s_data.width,
            height=s_data.height,
            steps=s_data.steps,
            cfg_scale=s_data.cfg_scale,
            sampler_name=s_data.sampler_name,
            seed=s_data.seed,
            clip_skip=s_data.clip_skip,
            context_tags=s_data.context_tags,
            # Consistency Enhancements
            use_reference_only=int(s_data.use_reference_only) if s_data.use_reference_only is not None else 1,
            reference_only_weight=s_data.reference_only_weight or 0.5,
            environment_reference_id=s_data.environment_reference_id,
            environment_reference_weight=s_data.environment_reference_weight or 0.3,
            candidates=s_data.candidates,  # Persist candidates
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

        # Handle MediaAsset for image_url
        if image_url:
            from config import MINIO_BUCKET
            path = urlparse(image_url).path
            if path.startswith("/"):
                path = path[1:]
            # Remove bucket prefix if present (MinIO/S3 URLs)
            if path.startswith(f"{MINIO_BUCKET}/"):
                path = path.replace(f"{MINIO_BUCKET}/", "", 1)
            if path.startswith("assets/"):
                path = path.replace("assets/", "", 1)
            storage_key = path

            # Check for existing asset to avoid IntegrityError
            asset = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()

            if not asset:
                asset = MediaAsset(
                    file_type="image",
                    storage_key=storage_key,
                    file_name=os.path.basename(storage_key),
                    mime_type="image/png", # Default
                    owner_type="scene",
                    owner_id=db_scene.id
                )
                db.add(asset)
                db.flush()
            else:
                # Update external references if needed (optional)
                # If asset exists but scene_id is different, we might want to update it?
                # But one asset belongs to one scene ideally (unless shared).
                # For now, just link it.
                pass

            db_scene.image_asset_id = asset.id
            # db_scene.image_url = image_url # Keep legacy field populated for now? Yes.


def _serialize_scene(scene: Scene) -> dict:
    """Serialize a Scene ORM object to dict for API response."""
    return {
        "id": scene.id,  # Actual DB primary key
        "scene_id": scene.order,  # Keep for backwards compatibility (scene order)
        "script": scene.script,
        "speaker": scene.speaker,
        "duration": scene.duration,
        "description": scene.description,
        "image_prompt": scene.image_prompt,
        "image_prompt_ko": scene.image_prompt_ko,
        "negative_prompt": scene.negative_prompt,
        "image_url": scene.image_asset.url if scene.image_asset else scene.image_url,
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
        "use_reference_only": scene.use_reference_only,
        "reference_only_weight": scene.reference_only_weight,
        "environment_reference_id": scene.environment_reference_id,
        "environment_reference_weight": scene.environment_reference_weight,
        "image_asset_id": scene.image_asset_id,
        "candidates": scene.candidates,  # Return candidates
    }


@router.post("/create")
async def create_storyboard_endpoint(request: StoryboardRequest):
    logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return create_storyboard(request)



def _truncate_title(title: str, max_length: int = 190) -> str:
    """Truncate title if it exceeds constraints."""
    if not title:
        return "Untitled"
    if len(title) > max_length:
        return title[:max_length] + "..."
    return title


@router.post("")
async def save_storyboard(request: StoryboardSave, db: Session = Depends(get_db)):
    """Save a full storyboard and its scenes to the DB."""
    safe_title = _truncate_title(request.title)
    logger.info("💾 [Storyboard Save] %s (truncated from %d chars)", safe_title, len(request.title))

    db_storyboard = Storyboard(
        title=safe_title,
        description=request.description,
        default_character_id=request.default_character_id,
        default_style_profile_id=request.default_style_profile_id,
    )
    db.add(db_storyboard)
    db.flush()

    _create_scenes(db, db_storyboard.id, request.scenes)

    db.commit()
    db.refresh(db_storyboard)

    # Return scene IDs for frontend to update local state
    scene_ids = [scene.id for scene in db_storyboard.scenes]

    return {
        "status": "success",
        "storyboard_id": db_storyboard.id,
        "scene_ids": scene_ids
    }


@router.get("")
def list_storyboards(db: Session = Depends(get_db)):
    """List all storyboards with scene/image counts."""
    storyboards = db.query(Storyboard).options(
        joinedload(Storyboard.scenes).joinedload(Scene.image_asset)
    ).all()

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
            joinedload(Storyboard.scenes).joinedload(Scene.image_asset),
        )
        .filter(Storyboard.id == storyboard_id)
        .first()
    )

    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    scenes = sorted(storyboard.scenes, key=lambda s: s.order)

    import json
    recent_videos = []
    if storyboard.recent_videos_json:
        try:
            recent_videos = json.loads(storyboard.recent_videos_json)
        except Exception:
            recent_videos = []

    return {
        "id": storyboard.id,
        "title": storyboard.title,
        "description": storyboard.description,
        "default_character_id": storyboard.default_character_id,
        "default_style_profile_id": storyboard.default_style_profile_id,
        "video_url": storyboard.video_url,
        "recent_videos": recent_videos,
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

    safe_title = _truncate_title(request.title)
    logger.info("✏️ [Storyboard Update] id=%d title=%s", storyboard_id, safe_title)

    # Update metadata
    storyboard.title = safe_title
    storyboard.description = request.description
    storyboard.default_character_id = request.default_character_id
    storyboard.default_style_profile_id = request.default_style_profile_id

    # 1. Nullify image_asset_id FK references first
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id).update(
        {Scene.image_asset_id: None}, synchronize_session=False
    )
    db.flush()

    # 2. Delete existing scenes (CASCADE removes tags & actions)
    # Get IDs of scenes to also delete their MediaAsset records
    scene_ids = [s.id for s in db.query(Scene).filter(Scene.storyboard_id == storyboard_id).all()]

    db.query(Scene).filter(Scene.storyboard_id == storyboard_id).delete()

    # 3. Now delete media_assets (no longer referenced)
    from models.media_asset import MediaAsset
    # Delete assets owned by the storyboard itself (like final video)
    db.query(MediaAsset).filter(
        MediaAsset.owner_type == "storyboard",
        MediaAsset.owner_id == storyboard_id
    ).delete()

    # Also delete assets owned by the deleted scenes
    if scene_ids:
        db.query(MediaAsset).filter(
            MediaAsset.owner_type == "scene",
            MediaAsset.owner_id.in_(scene_ids)
        ).delete()

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
