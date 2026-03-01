#!/usr/bin/env python3
"""Orphan MediaAsset Garbage Collection CLI.

Usage:
    python scripts/cleanup_orphan_assets.py              # dry-run (default)
    python scripts/cleanup_orphan_assets.py --execute     # actual deletion
    python scripts/cleanup_orphan_assets.py --candidates  # candidates JSONB only
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("cleanup_orphan_assets")


def _format_bytes(n: int | None) -> str:
    if not n or n <= 0:
        return "0 B"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _print_orphan_summary(report, label: str) -> None:
    """Print summary table for an orphan category."""
    if not report:
        log.info("  [%s] 0건", label)
        return
    total_size = sum(o.file_size or 0 for o in report)
    log.info("  [%s] %d건 (%s)", label, len(report), _format_bytes(total_size))
    for o in report[:10]:
        log.info("    - id=%d owner=%s/%s key=%s", o.id, o.owner_type, o.owner_id, o.storage_key)
    if len(report) > 10:
        log.info("    ... 외 %d건", len(report) - 10)


def run_orphan_cleanup(execute: bool) -> None:
    """Detect and optionally delete orphan MediaAssets."""
    from database import SessionLocal
    from services.media_gc import MediaGCService
    from services.storage import initialize_storage

    initialize_storage()
    db = SessionLocal()
    try:
        gc = MediaGCService(db)
        dry_run = not execute
        mode = "EXECUTE" if execute else "DRY-RUN"

        log.info("=== Orphan MediaAsset GC [%s] ===", mode)

        # 1) Detect
        report = gc.detect_orphans()
        log.info("--- 탐지 결과 ---")
        _print_orphan_summary(report.null_owner, "null_owner")
        _print_orphan_summary(report.broken_fk, "broken_fk")
        _print_orphan_summary(report.expired_temp, "expired_temp")

        all_orphans = report.null_owner + report.broken_fk
        total_size = sum(o.file_size or 0 for o in all_orphans)
        log.info("--- 총 orphan: %d건 (%s) ---", len(all_orphans), _format_bytes(total_size))

        if not all_orphans:
            log.info("정리할 orphan이 없습니다.")
            return

        # 2) Cleanup
        result = gc.cleanup_orphans(dry_run=dry_run)
        log.info("--- 결과 ---")
        log.info("  삭제: %d건 (dry_run=%s)", result.deleted, result.dry_run)
        if result.storage_errors:
            log.warning("  스토리지 에러: %d건", len(result.storage_errors))
            for e in result.storage_errors[:5]:
                log.warning("    %s", e)

        # 3) Expired temp
        temp_result = gc.cleanup_expired_temp(dry_run=dry_run)
        if temp_result.deleted:
            log.info("  만료 temp 삭제: %d건", temp_result.deleted)

    finally:
        db.close()


def run_candidates_cleanup(execute: bool) -> None:
    """Detect and optionally clean dangling candidates JSONB entries."""
    from database import SessionLocal
    from services.media_gc import MediaGCService

    db = SessionLocal()
    try:
        gc = MediaGCService(db)
        dry_run = not execute
        mode = "EXECUTE" if execute else "DRY-RUN"

        log.info("=== Dangling Candidates GC [%s] ===", mode)

        dangling = gc.detect_dangling_candidates()
        log.info("  dangling 항목: %d건", len(dangling))
        log.info("  영향 씬: %d개", len({d.scene_id for d in dangling}))

        for d in dangling[:10]:
            log.info("    scene_id=%d storyboard_id=%d asset_id=%d", d.scene_id, d.storyboard_id, d.media_asset_id)
        if len(dangling) > 10:
            log.info("    ... 외 %d건", len(dangling) - 10)

        if not dangling:
            log.info("정리할 dangling candidate가 없습니다.")
            return

        result = gc.cleanup_dangling_candidates(dry_run=dry_run)
        log.info("--- 결과 ---")
        log.info(
            "  제거: %d건, 영향 씬: %d개 (dry_run=%s)",
            result.candidates_removed,
            result.scenes_affected,
            result.dry_run,
        )

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Orphan MediaAsset Garbage Collection")
    parser.add_argument("--execute", action="store_true", help="실제 삭제 수행 (기본: dry-run)")
    parser.add_argument("--candidates", action="store_true", help="candidates JSONB dangling 정리만 수행")
    parser.add_argument("--all", action="store_true", help="orphan + candidates 모두 수행")
    args = parser.parse_args()

    if args.candidates:
        run_candidates_cleanup(args.execute)
    elif args.all:
        run_orphan_cleanup(args.execute)
        run_candidates_cleanup(args.execute)
    else:
        run_orphan_cleanup(args.execute)


if __name__ == "__main__":
    main()
