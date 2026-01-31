"""Video creation and management endpoints."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import VIDEO_DIR, logger
from database import get_db
from schemas import VideoDeleteRequest, VideoRequest
from services.utils import scrub_payload
from services.video import create_video_task

router = APIRouter(prefix="/video", tags=["video"])


@router.post("/create")
async def create_video(request: VideoRequest, db: Session = Depends(get_db)):
    logger.info("📥 [Video Req] %s", scrub_payload(request.model_dump()))
    res = await create_video_task(request)
    video_url = res.get("video_url")

    if video_url and request.storyboard_id:
        import json

        from models.storyboard import Storyboard

        storyboard = db.query(Storyboard).filter(Storyboard.id == request.storyboard_id).first()
        if storyboard:


            # Update recent_videos
            recent = []
            if storyboard.recent_videos_json:
                try:
                    recent = json.loads(storyboard.recent_videos_json)
                except Exception:
                    recent = []

            # Add new video to the beginning
            new_entry = {"url": video_url, "label": request.layout_style, "createdAt": int(time.time() * 1000)}
            recent = [new_entry] + recent[:9] # Keep last 10
            storyboard.recent_videos_json = json.dumps(recent)

            db.commit()
            logger.info("✅ Video associated with storyboard id=%d", request.storyboard_id)

    return res


@router.post("/delete")
async def delete_video(request: VideoDeleteRequest):
    filename = os.path.basename(request.filename or "")
    if not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    target = VIDEO_DIR / filename
    if not target.exists():
        return {"ok": False, "deleted": False, "reason": "not_found"}
    try:
        target.unlink()
        return {"ok": True, "deleted": True}
    except Exception as exc:
        logger.exception("Video delete failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/exists")
async def video_exists(filename: str = Query(..., min_length=1)):
    name = os.path.basename(filename)
    if not name.endswith(".mp4"):
        return {"exists": False}
    target = VIDEO_DIR / name
    return {"exists": target.exists()}


@router.get("/transitions")
async def get_transitions():
    """Get list of available scene transition effects."""
    from constants.transition import get_transition_list

    return {"transitions": get_transition_list()}
