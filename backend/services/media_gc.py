"""Media Asset Garbage Collection Service.

Detects and cleans up orphaned MediaAsset records:
- NULL owner: owner_type IS NULL
- Broken FK: owner_type set but owner_id not in master table
- Expired temp: is_temp=True and created_at older than TTL
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import MEDIA_ASSET_TEMP_TTL_SECONDS, logger
from models.character import Character
from models.lora import LoRA
from models.media_asset import MediaAsset
from models.project import Project
from models.scene import Scene
from models.sd_model import SDModel
from models.storyboard import Storyboard
from services.storage import get_storage

# owner_type → (master model class, FK columns referencing media_assets)
# FK columns are checked to protect assets referenced by direct FKs
OWNER_TYPE_MAP: dict[str, type] = {
    "project": Project,
    "character": Character,
    "storyboard": Storyboard,
    "scene": Scene,
}

# Direct FK references: (model, column_name) that point to media_assets.id
# Assets referenced here must never be treated as orphans
FK_REFERENCES: list[tuple[type, str]] = [
    (Project, "avatar_asset_id"),
    (Character, "preview_image_asset_id"),
    (LoRA, "preview_image_asset_id"),
    (SDModel, "preview_image_asset_id"),
    (Storyboard, "video_asset_id"),
    (Scene, "image_asset_id"),
]


@dataclass
class OrphanInfo:
    """Info about a single orphan asset."""
    id: int
    storage_key: str
    owner_type: str | None
    owner_id: int | None
    reason: str


@dataclass
class OrphanReport:
    """Result of orphan detection scan."""
    null_owner: list[OrphanInfo] = field(default_factory=list)
    broken_fk: list[OrphanInfo] = field(default_factory=list)
    expired_temp: list[OrphanInfo] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.null_owner) + len(self.broken_fk) + len(self.expired_temp)

    def to_dict(self) -> dict:
        def _serialize(items: list[OrphanInfo]) -> list[dict]:
            return [
                {"id": i.id, "storage_key": i.storage_key,
                 "owner_type": i.owner_type, "owner_id": i.owner_id,
                 "reason": i.reason}
                for i in items
            ]
        return {
            "null_owner": _serialize(self.null_owner),
            "broken_fk": _serialize(self.broken_fk),
            "expired_temp": _serialize(self.expired_temp),
            "total": self.total,
        }


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    deleted: int = 0
    storage_errors: list[str] = field(default_factory=list)
    dry_run: bool = True

    def to_dict(self) -> dict:
        return {
            "deleted": self.deleted,
            "storage_errors": self.storage_errors,
            "dry_run": self.dry_run,
        }


@dataclass
class GCStats:
    """Overall media asset statistics."""
    total_assets: int = 0
    temp_assets: int = 0
    null_owner_assets: int = 0
    orphan_count: int = 0
    by_owner_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_assets": self.total_assets,
            "temp_assets": self.temp_assets,
            "null_owner_assets": self.null_owner_assets,
            "orphan_count": self.orphan_count,
            "by_owner_type": self.by_owner_type,
        }


class MediaGCService:
    """Garbage collection for orphaned MediaAsset records."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_orphans(self) -> OrphanReport:
        """Scan for all orphan types and return a combined report."""
        report = OrphanReport()
        report.null_owner = self._detect_null_owner()
        report.broken_fk = self._detect_broken_fk()
        report.expired_temp = self._detect_expired_temp()
        return report

    def cleanup_orphans(self, *, dry_run: bool = True) -> CleanupResult:
        """Delete orphaned assets (null owner + broken FK).

        Args:
            dry_run: If True, only report what would be deleted.
        """
        report = OrphanReport()
        report.null_owner = self._detect_null_owner()
        report.broken_fk = self._detect_broken_fk()

        all_orphans = report.null_owner + report.broken_fk
        return self._delete_assets(all_orphans, dry_run=dry_run)

    def cleanup_expired_temp(self, *, dry_run: bool = True) -> CleanupResult:
        """Delete expired temporary assets.

        Args:
            dry_run: If True, only report what would be deleted.
        """
        expired = self._detect_expired_temp()
        return self._delete_assets(expired, dry_run=dry_run)

    def get_stats(self) -> GCStats:
        """Get overall media asset statistics."""
        stats = GCStats()
        stats.total_assets = self.db.query(MediaAsset).count()
        stats.temp_assets = self.db.query(MediaAsset).filter(
            MediaAsset.is_temp.is_(True),
        ).count()
        stats.null_owner_assets = self.db.query(MediaAsset).filter(
            MediaAsset.owner_type.is_(None),
        ).count()

        # Count by owner_type
        from sqlalchemy import func
        rows = (
            self.db.query(MediaAsset.owner_type, func.count(MediaAsset.id))
            .group_by(MediaAsset.owner_type)
            .all()
        )
        stats.by_owner_type = {
            (ot or "null"): cnt for ot, cnt in rows
        }

        # Orphan count (quick scan)
        report = self.detect_orphans()
        stats.orphan_count = report.total
        return stats

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _get_fk_referenced_ids(self) -> set[int]:
        """Collect all media_asset IDs that are directly referenced via FK columns."""
        referenced: set[int] = set()
        for model_cls, col_name in FK_REFERENCES:
            col = getattr(model_cls, col_name)
            rows = self.db.execute(
                select(col).where(col.isnot(None))
            ).scalars().all()
            referenced.update(rows)
        return referenced

    def _detect_null_owner(self) -> list[OrphanInfo]:
        """Find assets with owner_type IS NULL that aren't referenced by any FK."""
        protected_ids = self._get_fk_referenced_ids()

        assets = self.db.query(MediaAsset).filter(
            MediaAsset.owner_type.is_(None),
        ).all()

        return [
            OrphanInfo(
                id=a.id, storage_key=a.storage_key,
                owner_type=None, owner_id=None,
                reason="null_owner",
            )
            for a in assets
            if a.id not in protected_ids
        ]

    def _detect_broken_fk(self) -> list[OrphanInfo]:
        """Find assets whose owner_type/owner_id point to non-existent records."""
        orphans: list[OrphanInfo] = []

        for owner_type, model_cls in OWNER_TYPE_MAP.items():
            # Get all asset IDs with this owner_type
            assets = self.db.query(MediaAsset).filter(
                MediaAsset.owner_type == owner_type,
                MediaAsset.owner_id.isnot(None),
            ).all()

            if not assets:
                continue

            # Get all valid owner IDs from master table
            valid_ids = set(
                self.db.execute(select(model_cls.id)).scalars().all()
            )

            for a in assets:
                if a.owner_id not in valid_ids:
                    orphans.append(OrphanInfo(
                        id=a.id, storage_key=a.storage_key,
                        owner_type=a.owner_type, owner_id=a.owner_id,
                        reason=f"broken_fk:{owner_type}",
                    ))

        return orphans

    def _detect_expired_temp(self) -> list[OrphanInfo]:
        """Find temporary assets older than TTL."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=MEDIA_ASSET_TEMP_TTL_SECONDS,
        )

        assets = self.db.query(MediaAsset).filter(
            MediaAsset.is_temp.is_(True),
            MediaAsset.created_at < cutoff,
        ).all()

        return [
            OrphanInfo(
                id=a.id, storage_key=a.storage_key,
                owner_type=a.owner_type, owner_id=a.owner_id,
                reason="expired_temp",
            )
            for a in assets
        ]

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def _delete_with_storage(self, asset: MediaAsset) -> str | None:
        """Delete asset from storage, return error message or None."""
        try:
            storage = get_storage()
            storage.delete(asset.storage_key)
            return None
        except Exception as e:
            return f"storage_delete_failed:{asset.storage_key}:{e}"

    def _delete_assets(
        self, orphans: list[OrphanInfo], *, dry_run: bool = True,
    ) -> CleanupResult:
        """Delete a list of orphan assets from DB and storage."""
        result = CleanupResult(dry_run=dry_run)

        if dry_run:
            result.deleted = len(orphans)
            return result

        for info in orphans:
            asset = self.db.get(MediaAsset, info.id)
            if asset is None:
                continue

            # Delete from storage first
            err = self._delete_with_storage(asset)
            if err:
                result.storage_errors.append(err)
                logger.warning("GC storage error: %s", err)

            # Always delete DB record even if storage fails
            self.db.delete(asset)
            result.deleted += 1

        self.db.commit()
        return result
