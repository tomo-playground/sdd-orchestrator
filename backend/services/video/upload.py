"""Upload rendered video and register media asset.

Saves the final video file to object storage via AssetService and
returns the URL dict. Receives the VideoBuilder instance as its
first argument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import logger
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
            db.commit()

            url = asset_service.get_asset_url(asset.storage_key)
            logger.info(
                "[Video Build] Video uploaded and registered: %s",
                asset.storage_key,
            )
            return {"video_url": url, "media_asset_id": asset.id}
        finally:
            db.close()

    return {"video_url": f"/outputs/videos/{builder.video_filename}"}
