"""Admin endpoints for database management and media asset GC."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Tag
from schemas import (
    ActivateTagResponse,
    CacheRefreshResponse,
    DeprecatedTagsResponse,
    DeprecateTagResponse,
    ImageCacheClearResponse,
    ImageCacheStatsResponse,
    MediaCleanupResponse,
    MediaOrphanResponse,
    MediaStatsResponse,
    StorageCleanupResponse,
    StorageStatsResponse,
)
from services.media_gc import MediaGCService

router = APIRouter(tags=["admin"])


# ============================================================
# Pydantic Schemas
# ============================================================


class DeprecateTagRequest(BaseModel):
    """Request schema for deprecating a tag."""

    deprecated_reason: str
    replacement_tag_id: int | None = None


@router.post("/refresh-caches", response_model=CacheRefreshResponse)
async def refresh_all_caches(db: Session = Depends(get_db)):
    """Refresh all in-memory caches from database.

    Call this after migrating data to ensure caches are up-to-date.
    Returns 207 if some caches fail, 200 if all succeed.
    """
    from fastapi.responses import JSONResponse

    from services.keywords.db_cache import (
        LoRATriggerCache,
        TagAliasCache,
        TagCategoryCache,
        TagFilterCache,
        TagRuleCache,
        TagValenceCache,
    )

    caches = [
        ("TagCategoryCache", TagCategoryCache),
        ("TagFilterCache", TagFilterCache),
        ("TagAliasCache", TagAliasCache),
        ("TagRuleCache", TagRuleCache),
        ("TagValenceCache", TagValenceCache),
        ("LoRATriggerCache", LoRATriggerCache),
    ]

    refreshed = []
    failures = []
    for name, cache_cls in caches:
        try:
            cache_cls.refresh(db)
            refreshed.append(name)
        except Exception as e:
            logger.error("Cache refresh failed for %s: %s", name, e)
            failures.append({"cache": name, "error": f"{name} refresh failed"})

    if failures:
        return JSONResponse(
            status_code=207,
            content={
                "success": False,
                "message": f"{len(refreshed)} refreshed, {len(failures)} failed",
                "refreshed": refreshed,
                "failures": failures,
            },
        )
    return {"success": True, "message": "All caches refreshed successfully"}


# ============================================================
# Tag Valence Classification (Expression-Mood Conflict Detection)
# ============================================================


class ClassifyValenceResponse(BaseModel):
    ok: bool
    message: str


async def _run_valence_classification(group_names: list[str], force: bool) -> None:
    """Background task: LLM으로 태그 valence 일괄 분류."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        # Query tags in target groups that need valence classification
        query = db.query(Tag).filter(Tag.group_name.in_(group_names), Tag.is_active.is_(True))
        if not force:
            query = query.filter(Tag.valence.is_(None))
        tags_to_classify = query.all()

        if not tags_to_classify:
            logger.info("[Valence] No tags to classify")
            return

        tag_names = [t.name for t in tags_to_classify]
        logger.info("[Valence] Classifying %d tags: %s", len(tag_names), group_names)

        from services.tag_classifier import TagClassifier
        from services.tag_classifier_llm import classify_valence_via_llm

        results = await classify_valence_via_llm(tag_names)
        classifier = TagClassifier(db)
        saved = 0
        for r in results:
            classifier.save_valence(r["tag"], r["valence"], defer_commit=True)
            saved += 1

        if saved:
            try:
                db.commit()
            except Exception as e:
                logger.error("[Valence] Batch commit failed: %s", e)
                db.rollback()
                return

        # Refresh cache after classification
        from services.keywords.db_cache import TagValenceCache

        TagValenceCache.refresh(db)
        logger.info("[Valence] Classified %d/%d tags", saved, len(tag_names))
    except Exception as e:
        logger.error("[Valence] Classification failed: %s", e)
    finally:
        db.close()


@router.post("/tags/classify-valence", response_model=ClassifyValenceResponse)
async def classify_tag_valence(
    background_tasks: BackgroundTasks,
    group_names: str = Query("expression,gaze,mood", description="Comma-separated group names"),
    force: bool = Query(False, description="Re-classify even if valence already set"),
):
    """Batch-classify tag valence (emotion polarity) via LLM in background."""
    groups = [g.strip() for g in group_names.split(",") if g.strip()]
    if not groups:
        raise HTTPException(status_code=400, detail="At least one group_name required")

    background_tasks.add_task(_run_valence_classification, groups, force)
    return ClassifyValenceResponse(
        ok=True,
        message=f"Valence classification started (groups={groups}, force={force})",
    )


# ============================================================
# Tag Deprecation Management (Phase 6-4.15.8)
# ============================================================


@router.get("/tags/deprecated", response_model=DeprecatedTagsResponse)
async def get_deprecated_tags(db: Session = Depends(get_db)):
    """Get all deprecated tags with their replacement information."""
    deprecated_tags = db.query(Tag).filter(Tag.is_active.is_(False)).all()

    # Batch-load all replacement tags in a single IN query
    replacement_ids = [t.replacement_tag_id for t in deprecated_tags if t.replacement_tag_id]
    replacement_map: dict[int, Tag] = {}
    if replacement_ids:
        replacements = db.query(Tag).filter(Tag.id.in_(replacement_ids)).all()
        replacement_map = {t.id: t for t in replacements}

    result = []
    for tag in deprecated_tags:
        replacement = None
        if tag.replacement_tag_id:
            replacement_tag = replacement_map.get(tag.replacement_tag_id)
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


@router.put("/tags/{tag_id}/deprecate", response_model=DeprecateTagResponse)
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
        logger.exception("Failed to deprecate tag %d", tag_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e

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


@router.put("/tags/{tag_id}/activate", response_model=ActivateTagResponse)
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
        logger.exception("Failed to activate tag %d", tag_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e

    return {"success": True, "tag": {"id": tag.id, "name": tag.name, "is_active": tag.is_active}}


# ============================================================
# Media Asset Garbage Collection (Phase 6-7)
# ============================================================


@router.get("/media-assets/orphans", response_model=MediaOrphanResponse)
async def detect_orphan_assets(db: Session = Depends(get_db)):
    """Scan for orphaned media assets (dry-run detection only)."""
    try:
        gc = MediaGCService(db)
        report = gc.detect_orphans()
        return {"success": True, **report.to_dict()}
    except Exception:
        logger.exception("Orphan detection failed")
        return {"success": False, "error": "Orphan detection failed"}


@router.post("/media-assets/cleanup", response_model=MediaCleanupResponse)
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
    except Exception:
        db.rollback()
        logger.exception("Media cleanup failed")
        return {"success": False, "error": "Media cleanup failed"}


@router.get("/media-assets/stats", response_model=MediaStatsResponse)
async def media_asset_stats(db: Session = Depends(get_db)):
    """Get media asset statistics including orphan counts."""
    try:
        gc = MediaGCService(db)
        stats = gc.get_stats()
        return {"success": True, **stats.to_dict()}
    except Exception:
        logger.exception("Media stats failed")
        return {"success": False, "error": "Media stats retrieval failed"}


# ============================================================
# Image Generation Cache (Phase 4: Seed Anchoring)
# ============================================================


@router.get("/cache/images/stats", response_model=ImageCacheStatsResponse)
async def image_cache_stats():
    """Get image generation cache statistics."""
    from services.image_cache import get_cache_stats

    stats = get_cache_stats()
    return ImageCacheStatsResponse(**stats)


@router.delete("/cache/images", response_model=ImageCacheClearResponse)
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


@router.post("/tag-thumbnails/generate", response_model=TagThumbnailGenerateResponse)
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


@router.get("/storage/stats", response_model=StorageStatsResponse)
async def storage_stats():
    """Get storage statistics for all output directories."""
    from services.cleanup import get_storage_stats

    return get_storage_stats()


@router.post("/storage/cleanup", response_model=StorageCleanupResponse)
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


@router.post("/storage/cleanup/preview", response_model=StorageCleanupResponse)
async def cleanup_preview():
    """Preview what would be deleted without actually deleting."""
    from services.cleanup import CleanupOptions, cleanup_all

    options = CleanupOptions(dry_run=True)
    return cleanup_all(options)


# ------------------------------------------------------------------
# Checkpoint GC
# ------------------------------------------------------------------


class CheckpointGCResponse(BaseModel):
    deleted_threads: int
    retention_days: int
    deleted_rows: dict[str, int] | None = None


@router.post("/checkpoint-gc", response_model=CheckpointGCResponse)
async def run_checkpoint_gc(retention_days: int | None = Query(None, ge=1)):
    """Delete LangGraph checkpoint data older than retention period."""
    from services.agent.checkpointer import gc_checkpoints

    return await gc_checkpoints(retention_days)
