"""Upload rendered video and register media asset.

Saves the final video file to object storage via AssetService and
returns the URL dict. Receives the VideoBuilder instance as its
first argument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import VIDEO_DIR, logger
from database import SessionLocal
from services.asset_service import AssetService

if TYPE_CHECKING:
    from services.video.builder import VideoBuilder


def upload_result(builder: VideoBuilder) -> dict:
    """Upload and register the final video, return URL dict."""
    if builder.project_id_int and builder.group_id_int and builder.request.storyboard_id:
        db = SessionLocal()
        try:
            asset_service = AssetService(db)
            asset = asset_service.save_rendered_video(
                video_path=builder.video_path,
                project_id=builder.project_id_int,
                group_id=builder.group_id_int,
                storyboard_id=builder.request.storyboard_id,
                file_name=builder.video_filename,
            )
            # register_asset() already commits — no duplicate commit needed
            url = asset_service.get_asset_url(asset.storage_key)
            logger.info(
                "[Video Build] Video uploaded and registered: %s (asset_id=%d)",
                asset.storage_key,
                asset.id,
            )
            return {"video_url": url, "media_asset_id": asset.id}
        except Exception:
            logger.exception("[Video Build] S3 upload or asset registration failed")
            raise
        finally:
            db.close()

    # Fallback: local-only path (missing project/group/storyboard IDs)
    logger.warning(
        "[Video Build] Fallback to local path — missing IDs (project=%s, group=%s, storyboard=%s)",
        builder.project_id_int,
        builder.group_id_int,
        builder.request.storyboard_id,
    )
    return {"video_url": str(VIDEO_DIR / builder.video_filename)}
