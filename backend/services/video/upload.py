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


def _resolve_ids(builder: VideoBuilder) -> tuple[int | None, int | None, int | None]:
    """project/group/storyboard ID를 확정한다. 누락 시 DB에서 조회."""
    project_id = builder.project_id_int
    group_id = builder.group_id_int
    storyboard_id = builder.request.storyboard_id

    if storyboard_id and (not project_id or not group_id):
        try:
            from models import Storyboard  # noqa: PLC0415

            db = SessionLocal()
            try:
                sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
                if sb:
                    group_id = group_id or sb.group_id
                    if sb.group and sb.group.project_id:
                        project_id = project_id or sb.group.project_id
                    logger.info(
                        "[Video Build] IDs resolved from storyboard %d: project=%s, group=%s",
                        storyboard_id,
                        project_id,
                        group_id,
                    )
            finally:
                db.close()
        except Exception as e:
            logger.warning("[Video Build] ID resolve failed: %s", e)

    return project_id, group_id, storyboard_id


def upload_result(builder: VideoBuilder) -> dict:
    """Upload and register the final video, return URL dict."""
    project_id, group_id, storyboard_id = _resolve_ids(builder)

    if project_id and group_id and storyboard_id:
        db = SessionLocal()
        try:
            asset_service = AssetService(db)
            asset = asset_service.save_rendered_video(
                video_path=builder.video_path,
                project_id=project_id,
                group_id=group_id,
                storyboard_id=storyboard_id,
                file_name=builder.video_filename,
            )
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

    logger.warning(
        "[Video Build] Fallback to local path — missing IDs (project=%s, group=%s, storyboard=%s)",
        project_id,
        group_id,
        storyboard_id,
    )
    return {"video_url": str(VIDEO_DIR / builder.video_filename)}
