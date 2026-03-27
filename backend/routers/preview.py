"""Preview API: TTS preview, frame preview, timeline, pre-validation.

Service-only router (no admin endpoints).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    BatchTTSPreviewRequest,
    BatchTTSPreviewResponse,
    PreValidateRequest,
    PreValidateResponse,
    SceneFramePreviewRequest,
    SceneFramePreviewResponse,
    SceneTTSPreviewRequest,
    SceneTTSPreviewResponse,
    TimelineRequest,
    TimelineResponse,
)

service_router = APIRouter(prefix="/preview", tags=["preview"])


@service_router.post("/tts", response_model=SceneTTSPreviewResponse)
async def preview_tts(
    req: SceneTTSPreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate TTS preview for a single scene."""
    from services.error_responses import raise_user_error
    from services.preview import preview_scene_tts

    try:
        return await preview_scene_tts(req, db)
    except Exception as e:
        db.rollback()
        raise_user_error("tts_preview", e)


@service_router.post("/tts-batch", response_model=BatchTTSPreviewResponse)
async def preview_tts_batch(
    req: BatchTTSPreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate TTS previews for multiple scenes."""
    from services.error_responses import raise_user_error
    from services.preview import preview_batch_tts

    try:
        return await preview_batch_tts(req, db)
    except Exception as e:
        db.rollback()
        raise_user_error("tts_batch_preview", e)


@service_router.post("/frame", response_model=SceneFramePreviewResponse)
async def preview_frame(
    req: SceneFramePreviewRequest,
    db: Session = Depends(get_db),
):
    """Compose a scene frame preview (Pillow only, no FFmpeg)."""
    from services.error_responses import raise_user_error
    from services.preview import preview_scene_frame

    try:
        return await preview_scene_frame(req, db)
    except Exception as e:
        db.rollback()
        raise_user_error("frame_preview", e)


@service_router.post("/timeline", response_model=TimelineResponse)
async def preview_timeline(req: TimelineRequest):
    """Calculate timeline duration data for scenes."""
    from services.preview import preview_timeline

    return preview_timeline(req)


@service_router.post("/validate", response_model=PreValidateResponse)
async def validate_pre_render(
    req: PreValidateRequest,
    db: Session = Depends(get_db),
):
    """Run pre-render validation checks on a storyboard."""
    from services.error_responses import raise_user_error
    from services.preview import preview_validate

    try:
        return await preview_validate(req, db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise_user_error("pre_validate", e)
