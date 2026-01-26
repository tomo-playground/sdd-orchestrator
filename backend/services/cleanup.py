"""Storage cleanup service for managing output files.

Provides functions to analyze storage usage and clean up old/orphan files.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from config import (
    AVATAR_DIR,
    CACHE_DIR,
    CACHE_TTL_SECONDS,
    IMAGE_DIR,
    OUTPUT_DIR,
    VIDEO_DIR,
    logger,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class DirectoryStats:
    """Statistics for a single directory."""

    count: int = 0
    size_bytes: int = 0

    @property
    def size_mb(self) -> float:
        """Return size in megabytes."""
        return round(self.size_bytes / (1024 * 1024), 2)


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    deleted_count: int = 0
    freed_bytes: int = 0
    deleted_files: list[str] = field(default_factory=list)

    @property
    def freed_mb(self) -> float:
        """Return freed space in megabytes."""
        return round(self.freed_bytes / (1024 * 1024), 2)


def _iter_files(directory: Path) -> Iterator[Path]:
    """Iterate over all files in a directory recursively."""
    if not directory.exists():
        return
    for item in directory.rglob("*"):
        if item.is_file():
            yield item


def _get_dir_stats(directory: Path) -> DirectoryStats:
    """Get statistics for a directory."""
    stats = DirectoryStats()
    for file_path in _iter_files(directory):
        stats.count += 1
        try:
            stats.size_bytes += file_path.stat().st_size
        except OSError:
            pass
    return stats


def get_storage_stats() -> dict:
    """Get storage statistics for all output directories.

    Returns:
        Dictionary with total size and per-directory breakdown.
    """
    directories = {
        "videos": VIDEO_DIR,
        "images": IMAGE_DIR / "stored",
        "cache": CACHE_DIR,
        "avatars": AVATAR_DIR,
        "candidates": OUTPUT_DIR / "candidates",
    }

    result = {"directories": {}}
    total_size = 0
    total_count = 0

    for name, path in directories.items():
        stats = _get_dir_stats(path)
        result["directories"][name] = {
            "count": stats.count,
            "size_mb": stats.size_mb,
        }
        total_size += stats.size_bytes
        total_count += stats.count

    # Check for test folders
    test_folders = ["ffmpeg_test", "font_test"]
    for folder_name in test_folders:
        folder_path = OUTPUT_DIR / folder_name
        if folder_path.exists():
            stats = _get_dir_stats(folder_path)
            result["directories"][folder_name] = {
                "count": stats.count,
                "size_mb": stats.size_mb,
            }
            total_size += stats.size_bytes
            total_count += stats.count

    result["total_size_mb"] = round(total_size / (1024 * 1024), 2)
    result["total_count"] = total_count

    return result


def cleanup_old_videos(max_age_days: int = 7, dry_run: bool = False) -> CleanupResult:
    """Delete videos older than the specified age.

    Args:
        max_age_days: Maximum age in days. Files older than this will be deleted.
        dry_run: If True, only report what would be deleted without actually deleting.

    Returns:
        CleanupResult with details of deleted files.
    """
    result = CleanupResult()
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

    for file_path in _iter_files(VIDEO_DIR):
        try:
            mtime = file_path.stat().st_mtime
            if mtime < cutoff_time:
                size = file_path.stat().st_size
                result.deleted_files.append(str(file_path.relative_to(OUTPUT_DIR)))
                result.freed_bytes += size
                result.deleted_count += 1

                if not dry_run:
                    file_path.unlink()
                    logger.info("Deleted old video: %s", file_path)
        except OSError as e:
            logger.warning("Failed to process video file %s: %s", file_path, e)

    return result


def cleanup_old_images(max_age_days: int = 7, dry_run: bool = False) -> CleanupResult:
    """Delete images older than the specified age.

    Args:
        max_age_days: Maximum age in days. Files older than this will be deleted.
        dry_run: If True, only report what would be deleted without actually deleting.

    Returns:
        CleanupResult with details of deleted files.
    """
    result = CleanupResult()
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

    # Clean both root images and stored subfolder
    for file_path in _iter_files(IMAGE_DIR):
        if file_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
            
        try:
            mtime = file_path.stat().st_mtime
            if mtime < cutoff_time:
                size = file_path.stat().st_size
                result.deleted_files.append(str(file_path.relative_to(OUTPUT_DIR)))
                result.freed_bytes += size
                result.deleted_count += 1

                if not dry_run:
                    file_path.unlink()
                    logger.info("Deleted old image: %s", file_path)
        except OSError as e:
            logger.warning("Failed to process image file %s: %s", file_path, e)

    return result


def cleanup_cache(max_age_seconds: int | None = None, dry_run: bool = False) -> CleanupResult:
    """Delete cache files older than the specified age.

    Args:
        max_age_seconds: Maximum age in seconds. Defaults to CACHE_TTL_SECONDS.
        dry_run: If True, only report what would be deleted without actually deleting.

    Returns:
        CleanupResult with details of deleted files.
    """
    if max_age_seconds is None:
        max_age_seconds = CACHE_TTL_SECONDS

    result = CleanupResult()
    cutoff_time = time.time() - max_age_seconds

    for file_path in _iter_files(CACHE_DIR):
        try:
            mtime = file_path.stat().st_mtime
            if mtime < cutoff_time:
                size = file_path.stat().st_size
                result.deleted_files.append(str(file_path.relative_to(OUTPUT_DIR)))
                result.freed_bytes += size
                result.deleted_count += 1

                if not dry_run:
                    file_path.unlink()
                    logger.info("Deleted cache file: %s", file_path)
        except OSError as e:
            logger.warning("Failed to process cache file %s: %s", file_path, e)

    return result


def cleanup_test_folders(dry_run: bool = False) -> CleanupResult:
    """Delete all files in test folders (ffmpeg_test, font_test).

    Args:
        dry_run: If True, only report what would be deleted without actually deleting.

    Returns:
        CleanupResult with details of deleted files.
    """
    result = CleanupResult()
    test_folders = ["ffmpeg_test", "font_test"]

    for folder_name in test_folders:
        folder_path = OUTPUT_DIR / folder_name
        if not folder_path.exists():
            continue

        for file_path in _iter_files(folder_path):
            try:
                size = file_path.stat().st_size
                result.deleted_files.append(str(file_path.relative_to(OUTPUT_DIR)))
                result.freed_bytes += size
                result.deleted_count += 1

                if not dry_run:
                    file_path.unlink()
                    logger.info("Deleted test file: %s", file_path)
            except OSError as e:
                logger.warning("Failed to delete test file %s: %s", file_path, e)

        # Try to remove the empty directory
        if not dry_run:
            try:
                # Remove empty subdirectories first
                for subdir in sorted(folder_path.rglob("*"), reverse=True):
                    if subdir.is_dir():
                        try:
                            subdir.rmdir()
                        except OSError:
                            pass
                folder_path.rmdir()
                logger.info("Removed test folder: %s", folder_path)
            except OSError:
                pass  # Directory not empty or other error

    return result


def cleanup_candidates(dry_run: bool = False) -> CleanupResult:
    """Delete all candidate images (temporary generation results).

    Args:
        dry_run: If True, only report what would be deleted without actually deleting.

    Returns:
        CleanupResult with details of deleted files.
    """
    result = CleanupResult()
    candidates_dir = OUTPUT_DIR / "candidates"

    if not candidates_dir.exists():
        return result

    for file_path in _iter_files(candidates_dir):
        try:
            size = file_path.stat().st_size
            result.deleted_files.append(str(file_path.relative_to(OUTPUT_DIR)))
            result.freed_bytes += size
            result.deleted_count += 1

            if not dry_run:
                file_path.unlink()
                logger.info("Deleted candidate: %s", file_path)
        except OSError as e:
            logger.warning("Failed to delete candidate %s: %s", file_path, e)

    return result


@dataclass
class CleanupOptions:
    """Options for cleanup_all operation."""

    cleanup_videos: bool = True
    video_max_age_days: int = 7
    cleanup_images: bool = False
    image_max_age_days: int = 7
    cleanup_cache: bool = True
    cache_max_age_seconds: int | None = None
    cleanup_test_folders: bool = True
    cleanup_candidates: bool = False
    dry_run: bool = False


def cleanup_all(options: CleanupOptions) -> dict:
    """Perform cleanup based on the provided options.

    Args:
        options: CleanupOptions specifying what to clean and how.

    Returns:
        Dictionary with overall results and per-category details.
    """
    details = {}
    total_deleted = 0
    total_freed = 0

    if options.cleanup_videos:
        result = cleanup_old_videos(options.video_max_age_days, options.dry_run)
        details["videos"] = {
            "deleted": result.deleted_count,
            "freed_mb": result.freed_mb,
            "files": result.deleted_files if options.dry_run else [],
        }
        total_deleted += result.deleted_count
        total_freed += result.freed_bytes

    if options.cleanup_images:
        result = cleanup_old_images(options.image_max_age_days, options.dry_run)
        details["images"] = {
            "deleted": result.deleted_count,
            "freed_mb": result.freed_mb,
            "files": result.deleted_files if options.dry_run else [],
        }
        total_deleted += result.deleted_count
        total_freed += result.freed_bytes

    if options.cleanup_cache:
        result = cleanup_cache(options.cache_max_age_seconds, options.dry_run)
        details["cache"] = {
            "deleted": result.deleted_count,
            "freed_mb": result.freed_mb,
            "files": result.deleted_files if options.dry_run else [],
        }
        total_deleted += result.deleted_count
        total_freed += result.freed_bytes

    if options.cleanup_test_folders:
        result = cleanup_test_folders(options.dry_run)
        details["test_folders"] = {
            "deleted": result.deleted_count,
            "freed_mb": result.freed_mb,
            "files": result.deleted_files if options.dry_run else [],
        }
        total_deleted += result.deleted_count
        total_freed += result.freed_bytes

    if options.cleanup_candidates:
        result = cleanup_candidates(options.dry_run)
        details["candidates"] = {
            "deleted": result.deleted_count,
            "freed_mb": result.freed_mb,
            "files": result.deleted_files if options.dry_run else [],
        }
        total_deleted += result.deleted_count
        total_freed += result.freed_bytes

    return {
        "deleted_count": total_deleted,
        "freed_mb": round(total_freed / (1024 * 1024), 2),
        "dry_run": options.dry_run,
        "details": details,
    }
