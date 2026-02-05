"""YouTube video upload service."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from sqlalchemy.orm import Session

from database import SessionLocal
from models.render_history import RenderHistory
from services.youtube.auth import get_authenticated_service
from services.youtube.exceptions import YouTubeQuotaError, YouTubeUploadError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds


@dataclass
class UploadParams:
    """Parameters for YouTube upload (reduces function arg count)."""

    project_id: int
    render_history_id: int
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    privacy_status: str = "private"


def upload_video_to_youtube(params: UploadParams) -> None:
    """Upload video to YouTube (designed for BackgroundTasks).

    Creates its own DB session since the request session may be closed.
    Updates render_history with upload status on success/failure.
    """
    db: Session = SessionLocal()
    try:
        _do_upload(db, params)
    except Exception:
        logger.exception("YouTube upload failed for render_history %d", params.render_history_id)
        _mark_failed(db, params.render_history_id)
    finally:
        db.close()


def _do_upload(db: Session, params: UploadParams) -> None:
    """Core upload logic with retry."""
    rh = db.query(RenderHistory).filter(RenderHistory.id == params.render_history_id).first()
    if not rh:
        raise YouTubeUploadError(f"RenderHistory {params.render_history_id} not found")

    # Mark uploading
    rh.youtube_upload_status = "uploading"
    db.commit()

    # Resolve local video file path
    if not rh.media_asset:
        raise YouTubeUploadError("No media asset linked to this render")
    local_path = rh.media_asset.local_path
    if not local_path:
        raise YouTubeUploadError("No local video file found for this render")

    youtube = get_authenticated_service(db, params.project_id)

    body = {
        "snippet": {
            "title": params.title[:100],  # YouTube max 100 chars
            "description": params.description[:5000],
            "tags": params.tags[:500] if params.tags else [],
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": params.privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(local_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    video_id = _resumable_upload(request)

    # Mark success
    rh.youtube_video_id = video_id
    rh.youtube_upload_status = "completed"
    rh.youtube_uploaded_at = datetime.now(UTC)
    db.commit()
    logger.info("YouTube upload completed: video_id=%s, render_history=%d", video_id, params.render_history_id)


def _resumable_upload(request) -> str:
    """Execute resumable upload with exponential backoff retry."""
    for attempt in range(MAX_RETRIES):
        try:
            response = None
            while response is None:
                _, response = request.next_chunk()
            return response["id"]

        except HttpError as e:
            if e.resp.status == 403 and "quotaExceeded" in str(e):
                raise YouTubeQuotaError("YouTube API daily quota exceeded") from e
            if e.resp.status in (500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning("Upload HTTP %d, retrying in %ds (attempt %d)", e.resp.status, delay, attempt + 1)
                time.sleep(delay)
                continue
            raise YouTubeUploadError(f"YouTube API error: {e}") from e

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning("Upload error, retrying in %ds: %s", delay, e)
                time.sleep(delay)
                continue
            raise YouTubeUploadError(f"Upload failed after {MAX_RETRIES} attempts: {e}") from e

    raise YouTubeUploadError("Upload failed: max retries exceeded")


def _mark_failed(db: Session, render_history_id: int) -> None:
    """Mark upload as failed in DB."""
    try:
        rh = db.query(RenderHistory).filter(RenderHistory.id == render_history_id).first()
        if rh:
            rh.youtube_upload_status = "failed"
            db.commit()
    except Exception:
        logger.exception("Failed to mark upload status as failed")
