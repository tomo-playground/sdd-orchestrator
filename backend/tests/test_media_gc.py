"""Tests for Media Asset Garbage Collection service and admin endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from models import Character, MediaAsset, Project
from services.media_gc import MediaGCService

# ============================================================
# Fixtures
# ============================================================


def _make_asset(
    db_session,
    *,
    owner_type: str | None = None,
    owner_id: int | None = None,
    is_temp: bool = False,
    storage_key: str | None = None,
    created_at: datetime | None = None,
) -> MediaAsset:
    """Helper to create a MediaAsset in the test DB."""
    if storage_key is None:
        storage_key = f"test/{owner_type or 'none'}/{id(object())}.png"
    asset = MediaAsset(
        owner_type=owner_type,
        owner_id=owner_id,
        is_temp=is_temp,
        file_type="image",
        storage_key=storage_key,
        file_name="test.png",
    )
    if created_at is not None:
        asset.created_at = created_at
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


def _make_project(db_session, *, name: str = "test-project") -> Project:
    proj = Project(name=name)
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


def _make_character(db_session) -> Character:
    char = Character(name=f"test-char-{id(object())}", group_id=1)
    db_session.add(char)
    db_session.commit()
    db_session.refresh(char)
    return char


# ============================================================
# Detection Tests
# ============================================================


class TestDetectNullOwner:
    """Test detection of assets with NULL owner_type."""

    def test_detects_null_owner(self, db_session):
        _make_asset(db_session, storage_key="orphan/1.png")
        _make_asset(db_session, storage_key="orphan/2.png")

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.null_owner) == 2

    def test_skips_fk_referenced_null_owner(self, db_session):
        """Assets with NULL owner_type but referenced by FK should be protected."""
        char = Character(name="Test Char", group_id=1)
        db_session.add(char)
        db_session.flush()
        asset = _make_asset(db_session, storage_key="protected/preview.png")
        char.reference_image_asset_id = asset.id
        db_session.commit()

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.null_owner) == 0

    def test_no_false_positives_for_owned_assets(self, db_session):
        """Assets with valid owner_type should not appear in null_owner."""
        proj = _make_project(db_session)
        _make_asset(
            db_session,
            owner_type="project",
            owner_id=proj.id,
            storage_key="valid/1.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.null_owner) == 0


class TestDetectBrokenFK:
    """Test detection of assets with broken owner references."""

    def test_detects_broken_character_ref(self, db_session):
        """Asset points to character ID that doesn't exist."""
        _make_asset(
            db_session,
            owner_type="character",
            owner_id=99999,
            storage_key="broken/char.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.broken_fk) == 1
        assert report.broken_fk[0].reason == "broken_fk:character"

    def test_detects_broken_scene_ref(self, db_session):
        """Asset points to scene ID that doesn't exist."""
        _make_asset(
            db_session,
            owner_type="scene",
            owner_id=99999,
            storage_key="broken/scene.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.broken_fk) == 1
        assert report.broken_fk[0].reason == "broken_fk:scene"

    def test_valid_owner_not_detected(self, db_session):
        """Asset with valid owner reference should not be detected."""
        char = _make_character(db_session)
        _make_asset(
            db_session,
            owner_type="character",
            owner_id=char.id,
            storage_key="valid/char.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.broken_fk) == 0


class TestDetectExpiredTemp:
    """Test detection of expired temporary assets."""

    def test_detects_expired_temp(self, db_session):
        old_time = datetime.now(tz=UTC) - timedelta(days=2)
        _make_asset(
            db_session,
            is_temp=True,
            created_at=old_time,
            storage_key="temp/old.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.expired_temp) == 1

    def test_fresh_temp_not_detected(self, db_session):
        _make_asset(
            db_session,
            is_temp=True,
            storage_key="temp/fresh.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.expired_temp) == 0

    def test_non_temp_old_asset_not_detected(self, db_session):
        old_time = datetime.now(tz=UTC) - timedelta(days=2)
        _make_asset(
            db_session,
            is_temp=False,
            created_at=old_time,
            storage_key="perm/old.png",
        )

        gc = MediaGCService(db_session)
        report = gc.detect_orphans()
        assert len(report.expired_temp) == 0


# ============================================================
# Cleanup Tests
# ============================================================


class TestCleanupOrphans:
    """Test orphan cleanup operations."""

    @patch("services.media_gc.get_storage")
    def test_dry_run_does_not_delete(self, mock_get_storage, db_session):
        _make_asset(db_session, storage_key="orphan/dry.png")

        gc = MediaGCService(db_session)
        result = gc.cleanup_orphans(dry_run=True)

        assert result.deleted == 1
        assert result.dry_run is True
        # Asset should still exist
        assert db_session.query(MediaAsset).count() == 1
        mock_get_storage.assert_not_called()

    @patch("services.media_gc.get_storage")
    def test_actual_delete_removes_from_db(self, mock_get_storage, db_session):
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        _make_asset(db_session, storage_key="orphan/real.png")

        gc = MediaGCService(db_session)
        result = gc.cleanup_orphans(dry_run=False)

        assert result.deleted == 1
        assert result.dry_run is False
        assert db_session.query(MediaAsset).count() == 0
        mock_storage.delete.assert_called_once_with("orphan/real.png")

    @patch("services.media_gc.get_storage")
    def test_storage_error_tracked(self, mock_get_storage, db_session):
        mock_storage = MagicMock()
        mock_storage.delete.side_effect = Exception("S3 down")
        mock_get_storage.return_value = mock_storage

        _make_asset(db_session, storage_key="orphan/err.png")

        gc = MediaGCService(db_session)
        result = gc.cleanup_orphans(dry_run=False)

        # DB record should still be deleted
        assert result.deleted == 1
        assert len(result.storage_errors) == 1
        assert "S3 down" in result.storage_errors[0]
        assert db_session.query(MediaAsset).count() == 0


class TestCleanupExpiredTemp:
    """Test expired temp cleanup."""

    @patch("services.media_gc.get_storage")
    def test_cleanup_expired_temp(self, mock_get_storage, db_session):
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        old_time = datetime.now(tz=UTC) - timedelta(days=2)
        _make_asset(
            db_session,
            is_temp=True,
            created_at=old_time,
            storage_key="temp/expired.png",
        )
        _make_asset(db_session, is_temp=True, storage_key="temp/fresh.png")

        gc = MediaGCService(db_session)
        result = gc.cleanup_expired_temp(dry_run=False)

        assert result.deleted == 1
        # Fresh temp still exists
        assert db_session.query(MediaAsset).count() == 1


# ============================================================
# Stats Tests
# ============================================================


class TestGetStats:
    """Test stats collection."""

    def test_stats_counts(self, db_session):
        proj = _make_project(db_session)
        _make_asset(
            db_session,
            owner_type="project",
            owner_id=proj.id,
            storage_key="stats/valid.png",
        )
        _make_asset(db_session, is_temp=True, storage_key="stats/temp.png")
        _make_asset(db_session, storage_key="stats/orphan.png")

        gc = MediaGCService(db_session)
        stats = gc.get_stats()

        assert stats.total_assets == 3
        assert stats.temp_assets == 1
        assert stats.null_owner_assets == 2  # temp + orphan both have null owner
        assert stats.orphan_count >= 1


# ============================================================
# API Endpoint Tests
# ============================================================


class TestAdminEndpoints:
    """Test admin GC endpoints via TestClient."""

    def test_get_orphans(self, client, db_session):
        _make_asset(db_session, storage_key="api/orphan.png")

        response = client.get("/api/admin/media-assets/orphans")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] >= 1

    def test_cleanup_dry_run(self, client, db_session):
        _make_asset(db_session, storage_key="api/cleanup.png")

        response = client.post("/api/admin/media-assets/cleanup?dry_run=true")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_deleted"] >= 1
        # Asset should still exist (dry run)
        assert db_session.query(MediaAsset).count() == 1

    @patch("services.media_gc.get_storage")
    def test_cleanup_actual(self, mock_get_storage, client, db_session):
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        _make_asset(db_session, storage_key="api/delete.png")

        response = client.post("/api/admin/media-assets/cleanup?dry_run=false")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_stats(self, client, db_session):
        _make_asset(db_session, storage_key="api/stats.png")

        response = client.get("/api/admin/media-assets/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_assets"] >= 1
