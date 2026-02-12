"""YouTube OAuth and upload endpoints (project-scoped)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.render_history import RenderHistory
from models.youtube_credential import YouTubeCredential
from schemas import (
    YouTubeAuthURLResponse,
    YouTubeCredentialResponse,
    YouTubeRevokeResponse,
    YouTubeUploadRequest,
    YouTubeUploadStatusResponse,
)
from services.youtube.auth import exchange_code, generate_auth_url, revoke_credential
from services.youtube.exceptions import YouTubeAuthError
from services.youtube.upload import UploadParams, upload_video_to_youtube

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/authorize/{project_id}", response_model=YouTubeAuthURLResponse)
def authorize(project_id: int):
    """Generate Google OAuth URL for YouTube authorization."""
    try:
        auth_url = generate_auth_url(project_id)
        return YouTubeAuthURLResponse(auth_url=auth_url)
    except YouTubeAuthError as e:
        from services.error_responses import raise_user_error

        raise_user_error("youtube_auth", e)


@router.post("/callback", response_model=YouTubeCredentialResponse)
def callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Exchange OAuth authorization code for tokens."""
    try:
        project_id = int(state)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail="Invalid state parameter") from e
    try:
        cred = exchange_code(code, project_id, db)
        return cred
    except YouTubeAuthError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/credentials/{project_id}", response_model=YouTubeCredentialResponse)
def get_credential(project_id: int, db: Session = Depends(get_db)):
    """Get YouTube credential for a project."""
    cred = (
        db.query(YouTubeCredential)
        .filter(
            YouTubeCredential.project_id == project_id,
            YouTubeCredential.is_valid.is_(True),
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="No YouTube credential found")
    return cred


@router.delete("/credentials/{project_id}", response_model=YouTubeRevokeResponse)
def delete_credential(project_id: int, db: Session = Depends(get_db)):
    """Revoke YouTube credential for a project."""
    revoke_credential(db, project_id)
    return YouTubeRevokeResponse(status="revoked")


@router.post("/upload", response_model=YouTubeUploadStatusResponse)
def start_upload(
    body: YouTubeUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start asynchronous YouTube upload via BackgroundTasks."""
    rh = db.query(RenderHistory).filter(RenderHistory.id == body.render_history_id).first()
    if not rh:
        raise HTTPException(status_code=404, detail="Render history not found")

    # Check project YouTube credential exists
    cred = (
        db.query(YouTubeCredential)
        .filter(
            YouTubeCredential.project_id == body.project_id,
            YouTubeCredential.is_valid.is_(True),
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=400, detail="No valid YouTube credential for this project")

    # Check not already uploading or completed
    if rh.youtube_upload_status == "uploading":
        raise HTTPException(status_code=409, detail="Upload already in progress")
    if rh.youtube_upload_status == "completed" and rh.youtube_video_id:
        raise HTTPException(
            status_code=409,
            detail=f"Already uploaded (video ID: {rh.youtube_video_id})",
        )

    # Mark as uploading and schedule background task
    rh.youtube_upload_status = "uploading"
    db.commit()

    params = UploadParams(
        project_id=body.project_id,
        render_history_id=body.render_history_id,
        title=body.title,
        description=body.description,
        tags=body.tags,
        privacy_status=body.privacy_status,
    )
    background_tasks.add_task(upload_video_to_youtube, params)

    return YouTubeUploadStatusResponse(
        render_history_id=rh.id,
        youtube_video_id=rh.youtube_video_id,
        youtube_upload_status="uploading",
        youtube_uploaded_at=rh.youtube_uploaded_at,
    )


@router.get("/upload-status/{render_history_id}", response_model=YouTubeUploadStatusResponse)
def get_upload_status(render_history_id: int, db: Session = Depends(get_db)):
    """Poll upload status for a render history entry."""
    rh = db.query(RenderHistory).filter(RenderHistory.id == render_history_id).first()
    if not rh:
        raise HTTPException(status_code=404, detail="Render history not found")
    return YouTubeUploadStatusResponse(
        render_history_id=rh.id,
        youtube_video_id=rh.youtube_video_id,
        youtube_upload_status=rh.youtube_upload_status,
        youtube_uploaded_at=rh.youtube_uploaded_at,
    )
