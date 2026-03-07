"""Media Asset Garbage Collection Service.

Detects and cleans up orphaned MediaAsset records:
- NULL owner: owner_type IS NULL
- Broken FK: owner_type set but owner_id not in master table
- Expired temp: is_temp=True and created_at older than TTL
- Dangling candidates: JSONB media_asset_id referencing deleted assets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import MEDIA_ASSET_TEMP_TTL_SECONDS, logger
from models.background import Background
from models.character import Character
from models.lora import LoRA
from models.media_asset import MediaAsset
from models.project import Project
from models.render_history import RenderHistory
from models.scene import Scene
from models.sd_model import SDModel
from models.storyboard import Storyboard
from services.storage import get_storage

# owner_type -> master model class
OWNER_TYPE_MAP: dict[str, type] = {
    "project": Project,
    "character": Character,
    "storyboard": Storyboard,
    "scene": Scene,
    "background": Background,
}

# Direct FK references: (model, column_name) that point to media_assets.id
# Assets referenced here must never be treated as orphans
FK_REFERENCES: list[tuple[type, str]] = [
    (Background, "image_asset_id"),
    (Character, "reference_image_asset_id"),
    (LoRA, "preview_image_asset_id"),
    (SDModel, "preview_image_asset_id"),
    (RenderHistory, "media_asset_id"),
    (Scene, "image_asset_id"),
    (Scene, "environment_reference_id"),
    (Storyboard, "bgm_audio_asset_id"),
]


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass
class OrphanInfo:
    id: int
    storage_key: str
    owner_type: str | None
    owner_id: int | None
    reason: str
    file_size: int | None = None


@dataclass
class OrphanReport:
    null_owner: list[OrphanInfo] = field(default_factory=list)
    broken_fk: list[OrphanInfo] = field(default_factory=list)
    expired_temp: list[OrphanInfo] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.null_owner) + len(self.broken_fk) + len(self.expired_temp)

    def to_dict(self) -> dict:
        def _ser(items: list[OrphanInfo]) -> list[dict]:
            return [
                {
                    "id": i.id,
                    "storage_key": i.storage_key,
                    "owner_type": i.owner_type,
                    "owner_id": i.owner_id,
                    "reason": i.reason,
                }
                for i in items
            ]

        return {
            "null_owner": _ser(self.null_owner),
            "broken_fk": _ser(self.broken_fk),
            "expired_temp": _ser(self.expired_temp),
            "total": self.total,
        }


@dataclass
class CleanupResult:
    deleted: int = 0
    storage_errors: list[str] = field(default_factory=list)
    dry_run: bool = True

    def to_dict(self) -> dict:
        return {"deleted": self.deleted, "storage_errors": self.storage_errors, "dry_run": self.dry_run}


@dataclass
class DanglingCandidateInfo:
    scene_id: int
    storyboard_id: int
    media_asset_id: int


@dataclass
class DanglingCandidateResult:
    scenes_affected: int = 0
    candidates_removed: int = 0
    dry_run: bool = True

    def to_dict(self) -> dict:
        return {
            "scenes_affected": self.scenes_affected,
            "candidates_removed": self.candidates_removed,
            "dry_run": self.dry_run,
        }


@dataclass
class GCStats:
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


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class MediaGCService:
    """Garbage collection for orphaned MediaAsset records."""

    def __init__(self, db: Session):
        self.db = db

    # --- Public API ---

    def detect_orphans(self) -> OrphanReport:
        """Scan for all orphan types and return a combined report."""
        report = OrphanReport()
        report.null_owner = self._detect_null_owner()
        report.broken_fk = self._detect_broken_fk()
        report.expired_temp = self._detect_expired_temp()
        return report

    def cleanup_orphans(self, *, dry_run: bool = True) -> CleanupResult:
        """Delete orphaned assets (null owner + broken FK)."""
        report = OrphanReport()
        report.null_owner = self._detect_null_owner()
        report.broken_fk = self._detect_broken_fk()
        all_orphans = report.null_owner + report.broken_fk
        return self._delete_assets(all_orphans, dry_run=dry_run)

    def cleanup_expired_temp(self, *, dry_run: bool = True) -> CleanupResult:
        """Delete expired temporary assets."""
        expired = self._detect_expired_temp()
        return self._delete_assets(expired, dry_run=dry_run)

    def get_stats(self) -> GCStats:
        """Get overall media asset statistics."""
        stats = GCStats()
        stats.total_assets = self.db.query(MediaAsset).count()
        stats.temp_assets = self.db.query(MediaAsset).filter(MediaAsset.is_temp.is_(True)).count()
        stats.null_owner_assets = self.db.query(MediaAsset).filter(MediaAsset.owner_type.is_(None)).count()
        rows = self.db.query(MediaAsset.owner_type, func.count(MediaAsset.id)).group_by(MediaAsset.owner_type).all()
        stats.by_owner_type = {(ot or "null"): cnt for ot, cnt in rows}
        report = self.detect_orphans()
        stats.orphan_count = report.total
        return stats

    # --- Dangling Candidates ---

    def detect_dangling_candidates(self) -> list[DanglingCandidateInfo]:
        """Find candidates JSONB entries referencing non-existent MediaAssets."""
        scenes = self.db.query(Scene).filter(Scene.candidates.isnot(None), Scene.deleted_at.is_(None)).all()
        if not scenes:
            return []

        # Collect all referenced asset IDs
        candidate_ids: set[int] = set()
        for scene in scenes:
            for c in scene.candidates or []:
                aid = c.get("media_asset_id") if isinstance(c, dict) else None
                if aid:
                    candidate_ids.add(aid)

        if not candidate_ids:
            return []

        existing = set(self.db.execute(select(MediaAsset.id).where(MediaAsset.id.in_(candidate_ids))).scalars().all())
        dangling_ids = candidate_ids - existing
        if not dangling_ids:
            return []

        results: list[DanglingCandidateInfo] = []
        for scene in scenes:
            for c in scene.candidates or []:
                aid = c.get("media_asset_id") if isinstance(c, dict) else None
                if aid and aid in dangling_ids:
                    results.append(DanglingCandidateInfo(scene.id, scene.storyboard_id, aid))
        return results

    def cleanup_dangling_candidates(self, *, dry_run: bool = True) -> DanglingCandidateResult:
        """Remove candidates entries with dangling media_asset_ids."""
        dangling = self.detect_dangling_candidates()
        result = DanglingCandidateResult(dry_run=dry_run)
        result.candidates_removed = len(dangling)
        result.scenes_affected = len({d.scene_id for d in dangling})

        if not dangling or dry_run:
            return result

        # Group by scene for batch update
        by_scene: dict[int, set[int]] = {}
        for d in dangling:
            by_scene.setdefault(d.scene_id, set()).add(d.media_asset_id)

        for scene_id, bad_ids in by_scene.items():
            scene = self.db.get(Scene, scene_id)
            if not scene or not scene.candidates:
                continue
            cleaned = [c for c in scene.candidates if c.get("media_asset_id") not in bad_ids]
            scene.candidates = cleaned or None

        self.db.commit()
        return result

    # --- Detection helpers ---

    def _get_fk_referenced_ids(self) -> set[int]:
        """Collect all media_asset IDs directly referenced via FK columns."""
        referenced: set[int] = set()
        for model_cls, col_name in FK_REFERENCES:
            col = getattr(model_cls, col_name)
            rows = self.db.execute(select(col).where(col.isnot(None))).scalars().all()
            referenced.update(rows)
        return referenced

    def _detect_null_owner(self) -> list[OrphanInfo]:
        """Find assets with owner_type IS NULL not referenced by any FK."""
        protected = self._get_fk_referenced_ids()
        assets = self.db.query(MediaAsset).filter(MediaAsset.owner_type.is_(None)).all()
        return [
            OrphanInfo(a.id, a.storage_key, None, None, "null_owner", a.file_size)
            for a in assets
            if a.id not in protected
        ]

    def _detect_broken_fk(self) -> list[OrphanInfo]:
        """Find assets whose owner_type/owner_id point to non-existent records."""
        orphans: list[OrphanInfo] = []
        for owner_type, model_cls in OWNER_TYPE_MAP.items():
            assets = (
                self.db.query(MediaAsset)
                .filter(MediaAsset.owner_type == owner_type, MediaAsset.owner_id.isnot(None))
                .all()
            )
            if not assets:
                continue
            valid_ids = set(self.db.execute(select(model_cls.id)).scalars().all())
            for a in assets:
                if a.owner_id not in valid_ids:
                    orphans.append(
                        OrphanInfo(
                            a.id, a.storage_key, a.owner_type, a.owner_id, f"broken_fk:{owner_type}", a.file_size
                        )
                    )
        return orphans

    def _detect_expired_temp(self) -> list[OrphanInfo]:
        """Find temporary assets older than TTL."""
        cutoff = datetime.now(UTC) - timedelta(seconds=MEDIA_ASSET_TEMP_TTL_SECONDS)
        assets = self.db.query(MediaAsset).filter(MediaAsset.is_temp.is_(True), MediaAsset.created_at < cutoff).all()
        return [OrphanInfo(a.id, a.storage_key, a.owner_type, a.owner_id, "expired_temp", a.file_size) for a in assets]

    # --- Deletion ---

    def _delete_assets(self, orphans: list[OrphanInfo], *, dry_run: bool = True) -> CleanupResult:
        """Delete a list of orphan assets from DB and storage."""
        result = CleanupResult(dry_run=dry_run)
        if dry_run:
            result.deleted = len(orphans)
            return result

        storage = get_storage()
        for info in orphans:
            asset = self.db.get(MediaAsset, info.id)
            if asset is None:
                continue
            try:
                storage.delete(asset.storage_key)
            except Exception as e:
                err = f"storage_delete_failed:{asset.storage_key}:{e}"
                result.storage_errors.append(err)
                logger.warning("GC storage error: %s", err)
            self.db.delete(asset)
            result.deleted += 1

        self.db.commit()
        return result
