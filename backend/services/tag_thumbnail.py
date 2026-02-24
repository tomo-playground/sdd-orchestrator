"""Tag thumbnail service for Visual Tag Browser (Phase 15-B).

Fetches preview images from Danbooru, resizes to WebP thumbnails,
and stores them via AssetService with MediaAsset FK on Tag.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import time

import httpx
from PIL import Image
from sqlalchemy.orm import Session

from config import (
    DANBOORU_USER_AGENT,
    TAG_THUMBNAIL_BATCH_DELAY_MS,
    TAG_THUMBNAIL_QUALITY,
    TAG_THUMBNAIL_WIDTH,
    logger,
)
from models.tag import Tag
from services.asset_service import AssetService
from services.danbooru import get_post_image


def fetch_and_save_thumbnail(tag: Tag, db: Session) -> bool:
    """Fetch a Danbooru preview for *tag*, resize to WebP, and persist.

    Returns ``True`` on success, ``False`` otherwise.
    """
    if tag.thumbnail_asset_id:
        return True  # already has thumbnail

    post_info = asyncio.run(get_post_image(tag.name))
    if not post_info:
        logger.debug("[TagThumbnail] No image found for '%s'", tag.name)
        return False

    image_bytes = _download_image(post_info["preview_url"])
    if not image_bytes:
        return False

    webp_bytes = _resize_to_webp(image_bytes)
    if not webp_bytes:
        return False

    asset_svc = AssetService(db)
    digest = hashlib.sha1(webp_bytes).hexdigest()[:12]
    file_name = f"tag_{tag.id}_{digest}.webp"
    storage_key = f"tags/{tag.id}/thumbnail/{file_name}"

    from services.storage import get_storage

    get_storage().save(storage_key, webp_bytes, content_type="image/webp")
    asset = asset_svc.register_asset(
        file_name=file_name,
        file_type="image",
        storage_key=storage_key,
        owner_type="tag",
        owner_id=tag.id,
        file_size=len(webp_bytes),
        mime_type="image/webp",
    )

    tag.thumbnail_asset_id = asset.id
    db.commit()
    logger.info("[TagThumbnail] Saved thumbnail for '%s' (asset=%d)", tag.name, asset.id)
    return True


def generate_batch_thumbnails(
    db: Session,
    group_name: str | None = None,
    force: bool = False,
) -> dict:
    """Generate thumbnails for tags in a group (or all visual groups).

    Returns a summary dict with counts.
    """
    visual_groups = ["expression", "pose", "camera", "clothing", "hair_color", "hair_style"]
    query = db.query(Tag).filter(Tag.is_active.is_(True))

    if group_name:
        query = query.filter(Tag.group_name == group_name)
    else:
        query = query.filter(Tag.group_name.in_(visual_groups))

    if not force:
        query = query.filter(Tag.thumbnail_asset_id.is_(None))

    tags = query.all()
    succeeded = 0
    failed = 0
    delay_sec = TAG_THUMBNAIL_BATCH_DELAY_MS / 1000.0

    for tag in tags:
        try:
            ok = fetch_and_save_thumbnail(tag, db)
            if ok:
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning("[TagThumbnail] Error for '%s': %s", tag.name, e)
            failed += 1

        if delay_sec > 0:
            time.sleep(delay_sec)

    return {"total": len(tags), "succeeded": succeeded, "failed": failed}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _download_image(url: str) -> bytes | None:
    """Download an image from *url*, returning raw bytes or ``None``."""
    try:
        headers = {"User-Agent": DANBOORU_USER_AGENT}
        resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.debug("[TagThumbnail] Download failed (%s): %s", url, e)
        return None


def _resize_to_webp(image_bytes: bytes) -> bytes | None:
    """Resize image to ``TAG_THUMBNAIL_WIDTH`` square and encode as WebP."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        size = TAG_THUMBNAIL_WIDTH
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=TAG_THUMBNAIL_QUALITY)
        return buf.getvalue()
    except Exception as e:
        logger.debug("[TagThumbnail] Resize failed: %s", e)
        return None
