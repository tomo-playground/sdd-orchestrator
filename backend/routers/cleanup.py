"""Storage cleanup API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.cleanup import CleanupOptions, cleanup_all, get_storage_stats

router = APIRouter(prefix="/storage", tags=["storage"])


class CleanupRequest(BaseModel):
    """Request body for cleanup operation."""

    cleanup_videos: bool = Field(default=True, description="Clean up old videos")
    video_max_age_days: int = Field(default=7, ge=1, description="Max video age in days")
    cleanup_cache: bool = Field(default=True, description="Clean up expired prompt cache")
    cache_max_age_seconds: int | None = Field(
        default=None, description="Max cache age in seconds (default: CACHE_TTL_SECONDS)"
    )
    cleanup_build: bool = Field(default=True, description="Clean up old build workspaces")
    build_max_age_hours: int = Field(default=24, ge=1, description="Max build age in hours")
    cleanup_test_folders: bool = Field(default=True, description="Clean up test folders")
    dry_run: bool = Field(default=False, description="Preview only, don't delete")


@router.get("/stats")
async def storage_stats():
    """Get storage statistics for all output directories.

    Returns breakdown of file counts and sizes for:
    - videos: Rendered video files
    - images: Stored scene images
    - _prompt_cache: Prompt validation cache
    - _s3_cache: S3 local mirror cache
    - _build: Temporary build workspaces
    - shared: Shared assets (avatars, etc.)
    - test folders: ffmpeg_test, font_test if present
    """
    return get_storage_stats()


@router.post("/cleanup")
async def cleanup_storage(request: CleanupRequest):
    """Execute storage cleanup based on provided options.

    Permanently deletes files matching the criteria. Use dry_run=true to preview.
    """
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


@router.post("/cleanup/preview")
async def cleanup_preview(
    cleanup_videos: Annotated[bool, Query(description="Include old videos")] = True,
    video_max_age_days: Annotated[int, Query(ge=1, description="Max video age")] = 7,
    cleanup_cache: Annotated[bool, Query(description="Include expired cache")] = True,
    cleanup_build: Annotated[bool, Query(description="Include old build dirs")] = True,
    cleanup_test_folders: Annotated[bool, Query(description="Include test folders")] = True,
):
    """Preview what would be deleted without actually deleting.

    This is a convenience endpoint that always runs in dry_run mode.
    """
    options = CleanupOptions(
        cleanup_videos=cleanup_videos,
        video_max_age_days=video_max_age_days,
        cleanup_cache=cleanup_cache,
        cleanup_build=cleanup_build,
        cleanup_test_folders=cleanup_test_folders,
        dry_run=True,
    )
    return cleanup_all(options)
