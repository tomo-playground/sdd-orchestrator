"""Admin endpoints for database management and media asset GC."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Tag
from schemas import ImageCacheClearResponse, ImageCacheStatsResponse
from services.media_gc import MediaGCService

router = APIRouter(tags=["admin"])


# ============================================================
# Pydantic Schemas
# ============================================================


class DeprecateTagRequest(BaseModel):
    """Request schema for deprecating a tag."""

    deprecated_reason: str
    replacement_tag_id: int | None = None


@router.post("/admin/refresh-caches")
async def refresh_all_caches(db: Session = Depends(get_db)):
    """Refresh all in-memory caches from database.

    Call this after migrating data to ensure caches are up-to-date.
    """
    from services.keywords.core import TagFilterCache
    from services.keywords.db_cache import (
        LoRATriggerCache,
        TagAliasCache,
        TagCategoryCache,
        TagRuleCache,
    )

    try:
        TagCategoryCache.refresh(db)
        TagFilterCache.refresh(db)
        TagAliasCache.refresh(db)
        TagRuleCache.refresh(db)
        LoRATriggerCache.refresh(db)

        return {"success": True, "message": "All caches refreshed successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Tag Deprecation Management (Phase 6-4.15.8)
# ============================================================


@router.get("/admin/tags/deprecated")
async def get_deprecated_tags(db: Session = Depends(get_db)):
    """Get all deprecated tags with their replacement information."""
    deprecated_tags = db.query(Tag).filter(Tag.is_active.is_(False)).all()

    result = []
    for tag in deprecated_tags:
        replacement = None
        if tag.replacement_tag_id:
            replacement_tag = db.query(Tag).filter(Tag.id == tag.replacement_tag_id).first()
            if replacement_tag:
                replacement = {
                    "id": replacement_tag.id,
                    "name": replacement_tag.name,
                    "category": replacement_tag.category,
                }

        result.append(
            {
                "id": tag.id,
                "name": tag.name,
                "category": tag.category,
                "deprecated_reason": tag.deprecated_reason,
                "replacement": replacement,
                "created_at": tag.created_at.isoformat() if tag.created_at else None,
                "updated_at": tag.updated_at.isoformat() if tag.updated_at else None,
            }
        )

    return {"total": len(result), "tags": result}


@router.put("/admin/tags/{tag_id}/deprecate")
async def deprecate_tag(tag_id: int, request: DeprecateTagRequest, db: Session = Depends(get_db)):
    """Deprecate a tag and optionally set a replacement.

    Args:
        tag_id: ID of the tag to deprecate
        request: Deprecation details (reason, replacement_tag_id)

    Returns:
        Updated tag information
    """
    # Find tag
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")

    # Validate replacement tag if provided
    if request.replacement_tag_id:
        replacement = db.query(Tag).filter(Tag.id == request.replacement_tag_id).first()
        if not replacement:
            raise HTTPException(
                status_code=400, detail=f"Replacement tag with id {request.replacement_tag_id} not found"
            )
        if replacement.id == tag_id:
            raise HTTPException(status_code=400, detail="Cannot replace tag with itself")

    # Update tag
    tag.is_active = False
    tag.deprecated_reason = request.deprecated_reason
    tag.replacement_tag_id = request.replacement_tag_id

    try:
        db.commit()
        db.refresh(tag)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e

    return {
        "success": True,
        "tag": {
            "id": tag.id,
            "name": tag.name,
            "is_active": tag.is_active,
            "deprecated_reason": tag.deprecated_reason,
            "replacement_tag_id": tag.replacement_tag_id,
        },
    }


@router.put("/admin/tags/{tag_id}/activate")
async def activate_tag(tag_id: int, db: Session = Depends(get_db)):
    """Reactivate a deprecated tag.

    Args:
        tag_id: ID of the tag to activate

    Returns:
        Updated tag information
    """
    # Find tag
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")

    # Update tag
    tag.is_active = True
    tag.deprecated_reason = None
    tag.replacement_tag_id = None

    try:
        db.commit()
        db.refresh(tag)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e

    return {"success": True, "tag": {"id": tag.id, "name": tag.name, "is_active": tag.is_active}}


# ============================================================
# Media Asset Garbage Collection (Phase 6-7)
# ============================================================


@router.get("/admin/media-assets/orphans")
async def detect_orphan_assets(db: Session = Depends(get_db)):
    """Scan for orphaned media assets (dry-run detection only)."""
    try:
        gc = MediaGCService(db)
        report = gc.detect_orphans()
        return {"success": True, **report.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/admin/media-assets/cleanup")
async def cleanup_orphan_assets(
    dry_run: bool = True,
    db: Session = Depends(get_db),
):
    """Clean up orphaned and expired temporary media assets.

    Args:
        dry_run: If True (default), only report what would be deleted.
    """
    try:
        gc = MediaGCService(db)
        orphan_result = gc.cleanup_orphans(dry_run=dry_run)
        temp_result = gc.cleanup_expired_temp(dry_run=dry_run)
        return {
            "success": True,
            "orphans": orphan_result.to_dict(),
            "expired_temp": temp_result.to_dict(),
            "total_deleted": orphan_result.deleted + temp_result.deleted,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


@router.get("/admin/media-assets/stats")
async def media_asset_stats(db: Session = Depends(get_db)):
    """Get media asset statistics including orphan counts."""
    try:
        gc = MediaGCService(db)
        stats = gc.get_stats()
        return {"success": True, **stats.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Image Generation Cache (Phase 4: Seed Anchoring)
# ============================================================


@router.get("/admin/cache/images/stats", response_model=ImageCacheStatsResponse)
async def image_cache_stats():
    """Get image generation cache statistics."""
    from services.image_cache import get_cache_stats

    stats = get_cache_stats()
    return ImageCacheStatsResponse(**stats)


@router.delete("/admin/cache/images", response_model=ImageCacheClearResponse)
async def clear_image_cache_endpoint():
    """Clear all cached generated images."""
    from services.image_cache import clear_image_cache

    count = clear_image_cache()
    return ImageCacheClearResponse(cleared=count)


# ============================================================
# Tag Thumbnail Batch Generation (Phase 15-B)
# ============================================================


class TagThumbnailGenerateResponse(BaseModel):
    ok: bool
    message: str


def _run_thumbnail_generation(group_name: str | None, force: bool) -> None:
    """Run thumbnail generation in background with its own DB session."""
    from database import SessionLocal
    from services.tag_thumbnail import generate_batch_thumbnails

    db = SessionLocal()
    try:
        generate_batch_thumbnails(db, group_name, force)
    finally:
        db.close()


@router.post("/admin/tag-thumbnails/generate", response_model=TagThumbnailGenerateResponse)
async def generate_tag_thumbnails(
    background_tasks: BackgroundTasks,
    group_name: str | None = Query(None, description="Filter by group_name (e.g. expression, pose)"),
    force: bool = Query(False, description="Re-generate even if thumbnail already exists"),
):
    """Batch-generate tag thumbnails from Danbooru in background."""
    valid_groups = {
        "expression",
        "pose",
        "camera",
        "hair_color",
        "hair_style",
        "clothing_top",
        "clothing_bottom",
        "clothing_outfit",
        "clothing_detail",
        "legwear",
        "footwear",
        "accessory",
    }
    if group_name and group_name not in valid_groups:
        raise HTTPException(status_code=400, detail=f"Invalid group_name. Must be one of: {sorted(valid_groups)}")

    background_tasks.add_task(_run_thumbnail_generation, group_name, force)
    return TagThumbnailGenerateResponse(
        ok=True, message=f"Thumbnail generation started (group={group_name or 'all'}, force={force})"
    )


# ============================================================
# Storage Cleanup (absorbed from cleanup.py)
# ============================================================


class CleanupRequest(BaseModel):
    """Request body for cleanup operation."""

    cleanup_videos: bool = True
    video_max_age_days: int = 7
    cleanup_cache: bool = True
    cache_max_age_seconds: int | None = None
    cleanup_build: bool = True
    build_max_age_hours: int = 24
    cleanup_test_folders: bool = True
    dry_run: bool = False


@router.get("/storage/stats")
async def storage_stats():
    """Get storage statistics for all output directories."""
    from services.cleanup import get_storage_stats

    return get_storage_stats()


@router.post("/storage/cleanup")
async def cleanup_storage(request: CleanupRequest):
    """Execute storage cleanup based on provided options."""
    from services.cleanup import CleanupOptions, cleanup_all

    options = CleanupOptions(
        cleanup_videos=request.cleanup_videos,
        video_max_age_days=request.video_max_age_days,
        cleanup_cache=request.cleanup_cache,
        cache_max_age_seconds=request.cache_max_age_seconds,
        cleanup_build=request.cleanup_build,
        build_max_age_hours=request.build_max_age_hours,
        cleanup_test_folders=request.cleanup_test_folders,
        dry_run=request.dry_run,
    )
    return cleanup_all(options)


@router.post("/storage/cleanup/preview")
async def cleanup_preview():
    """Preview what would be deleted without actually deleting."""
    from services.cleanup import CleanupOptions, cleanup_all

    options = CleanupOptions(dry_run=True)
    return cleanup_all(options)
