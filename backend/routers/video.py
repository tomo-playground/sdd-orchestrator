"""Video creation and management endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query

from services.video import create_video_task
from services.utils import scrub_payload

router = APIRouter(prefix="/video", tags=["video"])


@router.post("/create")
async def create_video(request: VideoRequest):
    logger.info("📥 [Video Req] %s", scrub_payload(request.model_dump()))
    return await create_video_task(request)


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
        raise HTTPException(status_code=500, detail=str(exc))


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
