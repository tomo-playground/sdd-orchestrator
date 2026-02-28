"""Unit tests for backend/services/storyboard/crud.py.

Uses SQLite in-memory DB via conftest.py fixtures (db_session, test_group).
All external services are mocked to ensure isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from models.scene import Scene
from models.storyboard import Storyboard
from schemas import StoryboardSave, StoryboardUpdate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_save_request(
    title: str = "Test Storyboard",
    group_id: int = 1,
    scenes: list | None = None,
    **kwargs,
) -> StoryboardSave:
    """Create a StoryboardSave request with defaults."""
    return StoryboardSave(
        title=title,
        group_id=group_id,
        scenes=scenes or [],
        **kwargs,
    )


# ===========================================================================
# 1. save_storyboard_to_db
# ===========================================================================


class TestSaveStoryboardToDb:
    """Tests for save_storyboard_to_db()."""

    @patch("services.storyboard.scene_builder.create_scenes")
    @patch("services.characters.assign_speakers")
    @patch("services.seed_anchoring.generate_base_seed", return_value=12345)
    def test_creates_storyboard(self, mock_seed, mock_assign, mock_scenes, db_session):
        from services.storyboard.crud import save_storyboard_to_db

        request = _make_save_request(title="My Story")
        result = save_storyboard_to_db(db_session, request)

        assert result["status"] == "success"
        assert "storyboard_id" in result
        assert result["version"] == 1

    @patch("services.storyboard.scene_builder.create_scenes")
    @patch("services.characters.assign_speakers")
    @patch("services.seed_anchoring.generate_base_seed", return_value=12345)
    def test_requires_group_id(self, mock_seed, mock_assign, mock_scenes, db_session):
        from services.storyboard.crud import save_storyboard_to_db

        request = _make_save_request(group_id=None)
        with pytest.raises(HTTPException) as exc_info:
            save_storyboard_to_db(db_session, request)
        assert exc_info.value.status_code == 400

    @patch("services.storyboard.scene_builder.create_scenes")
    @patch("services.characters.assign_speakers")
    @patch("services.seed_anchoring.generate_base_seed", return_value=12345)
    def test_truncates_long_title(self, mock_seed, mock_assign, mock_scenes, db_session):
        from services.storyboard.crud import save_storyboard_to_db

        long_title = "T" * 200
        request = _make_save_request(title=long_title)
        result = save_storyboard_to_db(db_session, request)

        sb = db_session.query(Storyboard).filter_by(id=result["storyboard_id"]).first()
        assert len(sb.title) <= 200

    @patch("services.storyboard.scene_builder.create_scenes")
    @patch("services.characters.assign_speakers")
    @patch("services.seed_anchoring.generate_base_seed", return_value=42)
    def test_returns_scene_ids_and_client_ids(self, mock_seed, mock_assign, mock_scenes, db_session):
        from services.storyboard.crud import save_storyboard_to_db

        request = _make_save_request()
        result = save_storyboard_to_db(db_session, request)

        assert "scene_ids" in result
        assert "client_ids" in result
        assert isinstance(result["scene_ids"], list)
        assert isinstance(result["client_ids"], list)


# ===========================================================================
# 2. get_storyboard_by_id
# ===========================================================================


class TestGetStoryboardById:
    """Tests for get_storyboard_by_id()."""

    def _create_storyboard(self, db_session, title="Test SB") -> int:
        sb = Storyboard(title=title, group_id=1)
        db_session.add(sb)
        db_session.commit()
        db_session.refresh(sb)
        return sb.id

    @patch("services.characters.resolve_speaker_to_character", return_value=None)
    @patch("services.config_resolver.resolve_effective_config", return_value={"values": {}})
    def test_returns_storyboard_dict(self, mock_config, mock_speaker, db_session):
        from services.storyboard.crud import get_storyboard_by_id

        sb_id = self._create_storyboard(db_session)
        result = get_storyboard_by_id(db_session, sb_id)

        assert result["id"] == sb_id
        assert result["title"] == "Test SB"
        assert "scenes" in result

    @patch("services.characters.resolve_speaker_to_character", return_value=None)
    @patch("services.config_resolver.resolve_effective_config", return_value={"values": {}})
    def test_404_for_nonexistent_id(self, mock_config, mock_speaker, db_session):
        from services.storyboard.crud import get_storyboard_by_id

        with pytest.raises(HTTPException) as exc_info:
            get_storyboard_by_id(db_session, 99999)
        assert exc_info.value.status_code == 404

    @patch("services.characters.resolve_speaker_to_character", return_value=None)
    @patch("services.config_resolver.resolve_effective_config", return_value={"values": {}})
    def test_404_for_soft_deleted(self, mock_config, mock_speaker, db_session):
        from services.storyboard.crud import get_storyboard_by_id

        sb = Storyboard(title="Deleted SB", group_id=1, deleted_at=datetime.now(UTC))
        db_session.add(sb)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            get_storyboard_by_id(db_session, sb.id)
        assert exc_info.value.status_code == 404


# ===========================================================================
# 3. list_storyboards_from_db
# ===========================================================================


class TestListStoryboardsFromDb:
    """Tests for list_storyboards_from_db()."""

    def test_empty_list(self, db_session):
        from services.storyboard.crud import list_storyboards_from_db

        result = list_storyboards_from_db(db_session)
        assert result["items"] == []
        assert result["total"] == 0

    def test_lists_storyboards(self, db_session):
        from services.storyboard.crud import list_storyboards_from_db

        sb1 = Storyboard(title="SB 1", group_id=1)
        sb2 = Storyboard(title="SB 2", group_id=1)
        db_session.add_all([sb1, sb2])
        db_session.commit()

        result = list_storyboards_from_db(db_session)
        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_filters_by_group_id(self, db_session):
        from services.storyboard.crud import list_storyboards_from_db

        sb1 = Storyboard(title="SB Group 1", group_id=1)
        db_session.add(sb1)
        db_session.commit()

        result = list_storyboards_from_db(db_session, group_id=1)
        assert result["total"] >= 1

        result_other = list_storyboards_from_db(db_session, group_id=9999)
        assert result_other["total"] == 0

    def test_excludes_soft_deleted(self, db_session):
        from services.storyboard.crud import list_storyboards_from_db

        sb = Storyboard(title="Deleted", group_id=1, deleted_at=datetime.now(UTC))
        db_session.add(sb)
        db_session.commit()

        result = list_storyboards_from_db(db_session)
        titles = [item["title"] for item in result["items"]]
        assert "Deleted" not in titles

    def test_pagination(self, db_session):
        from services.storyboard.crud import list_storyboards_from_db

        for i in range(5):
            db_session.add(Storyboard(title=f"SB {i}", group_id=1))
        db_session.commit()

        result = list_storyboards_from_db(db_session, offset=0, limit=2)
        assert len(result["items"]) == 2
        assert result["total"] == 5
        assert result["offset"] == 0
        assert result["limit"] == 2


# ===========================================================================
# 4. update_storyboard_metadata
# ===========================================================================


class TestUpdateStoryboardMetadata:
    """Tests for update_storyboard_metadata()."""

    def _create_storyboard(self, db_session) -> int:
        sb = Storyboard(title="Original Title", group_id=1)
        db_session.add(sb)
        db_session.commit()
        db_session.refresh(sb)
        return sb.id

    def test_updates_title(self, db_session):
        from services.storyboard.crud import update_storyboard_metadata

        sb_id = self._create_storyboard(db_session)
        request = StoryboardUpdate(title="New Title")
        result = update_storyboard_metadata(db_session, sb_id, request)

        assert result["status"] == "success"
        sb = db_session.query(Storyboard).filter_by(id=sb_id).first()
        assert sb.title == "New Title"

    def test_increments_version(self, db_session):
        from services.storyboard.crud import update_storyboard_metadata

        sb_id = self._create_storyboard(db_session)
        request = StoryboardUpdate(title="V2")
        result = update_storyboard_metadata(db_session, sb_id, request)

        assert result["version"] == 2

    def test_optimistic_locking_conflict(self, db_session):
        from services.storyboard.crud import update_storyboard_metadata

        sb_id = self._create_storyboard(db_session)
        request = StoryboardUpdate(title="Conflict", version=99)

        with pytest.raises(HTTPException) as exc_info:
            update_storyboard_metadata(db_session, sb_id, request)
        assert exc_info.value.status_code == 409

    def test_404_for_nonexistent(self, db_session):
        from services.storyboard.crud import update_storyboard_metadata

        request = StoryboardUpdate(title="Nope")
        with pytest.raises(HTTPException) as exc_info:
            update_storyboard_metadata(db_session, 99999, request)
        assert exc_info.value.status_code == 404


# ===========================================================================
# 5. delete_storyboard_from_db (soft delete)
# ===========================================================================


class TestDeleteStoryboardFromDb:
    """Tests for delete_storyboard_from_db()."""

    def _create_storyboard(self, db_session) -> int:
        sb = Storyboard(title="To Delete", group_id=1)
        db_session.add(sb)
        db_session.commit()
        db_session.refresh(sb)
        return sb.id

    def test_soft_deletes_storyboard(self, db_session):
        from services.storyboard.crud import delete_storyboard_from_db

        sb_id = self._create_storyboard(db_session)
        result = delete_storyboard_from_db(db_session, sb_id)

        assert result["status"] == "success"
        sb = db_session.query(Storyboard).filter_by(id=sb_id).first()
        assert sb.deleted_at is not None

    def test_cascades_to_scenes(self, db_session):
        from services.storyboard.crud import delete_storyboard_from_db

        sb_id = self._create_storyboard(db_session)
        scene = Scene(storyboard_id=sb_id, order=0, script="scene 1")
        db_session.add(scene)
        db_session.commit()

        delete_storyboard_from_db(db_session, sb_id)

        scene_refreshed = db_session.query(Scene).filter_by(id=scene.id).first()
        assert scene_refreshed.deleted_at is not None

    def test_404_for_nonexistent(self, db_session):
        from services.storyboard.crud import delete_storyboard_from_db

        with pytest.raises(HTTPException) as exc_info:
            delete_storyboard_from_db(db_session, 99999)
        assert exc_info.value.status_code == 404

    def test_404_for_already_deleted(self, db_session):
        from services.storyboard.crud import delete_storyboard_from_db

        sb = Storyboard(title="Already gone", group_id=1, deleted_at=datetime.now(UTC))
        db_session.add(sb)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            delete_storyboard_from_db(db_session, sb.id)
        assert exc_info.value.status_code == 404


# ===========================================================================
# 6. restore_storyboard_from_db
# ===========================================================================


class TestRestoreStoryboardFromDb:
    """Tests for restore_storyboard_from_db()."""

    def test_restores_soft_deleted(self, db_session):
        from services.storyboard.crud import restore_storyboard_from_db

        ts = datetime.now(UTC)
        sb = Storyboard(title="Trashed", group_id=1, deleted_at=ts)
        db_session.add(sb)
        db_session.commit()

        result = restore_storyboard_from_db(db_session, sb.id)
        assert result["ok"] is True

        sb_refreshed = db_session.query(Storyboard).filter_by(id=sb.id).first()
        assert sb_refreshed.deleted_at is None

    def test_restores_batch_deleted_scenes(self, db_session):
        from services.storyboard.crud import restore_storyboard_from_db

        ts = datetime.now(UTC)
        sb = Storyboard(title="Trashed SB", group_id=1, deleted_at=ts)
        db_session.add(sb)
        db_session.flush()

        scene = Scene(storyboard_id=sb.id, order=0, script="s1", deleted_at=ts)
        db_session.add(scene)
        db_session.commit()

        restore_storyboard_from_db(db_session, sb.id)
        scene_refreshed = db_session.query(Scene).filter_by(id=scene.id).first()
        assert scene_refreshed.deleted_at is None

    def test_404_for_non_deleted(self, db_session):
        from services.storyboard.crud import restore_storyboard_from_db

        sb = Storyboard(title="Active", group_id=1)
        db_session.add(sb)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            restore_storyboard_from_db(db_session, sb.id)
        assert exc_info.value.status_code == 404


# ===========================================================================
# 7. _derive_kanban_status
# ===========================================================================


class TestDeriveKanbanStatus:
    """Tests for _derive_kanban_status()."""

    def test_draft_when_no_images(self, db_session):
        from services.storyboard.crud import _derive_kanban_status

        sb = Storyboard(title="Draft", group_id=1)
        db_session.add(sb)
        db_session.commit()
        db_session.refresh(sb)

        result = _derive_kanban_status(sb, image_count=0)
        assert result == "draft"

    def test_in_prod_with_images(self, db_session):
        from services.storyboard.crud import _derive_kanban_status

        sb = Storyboard(title="InProd", group_id=1)
        db_session.add(sb)
        db_session.commit()
        db_session.refresh(sb)

        result = _derive_kanban_status(sb, image_count=3)
        assert result == "in_prod"

    def _create_render_history(self, db_session, sb_id, youtube_video_id=None):
        """Helper to create a RenderHistory with required MediaAsset."""
        from models.media_asset import MediaAsset
        from models.render_history import RenderHistory

        asset = MediaAsset(
            storage_key="test/video.mp4",
            file_name="video.mp4",
            file_type="video",
            owner_type="storyboard",
            owner_id=sb_id,
        )
        db_session.add(asset)
        db_session.flush()

        rh = RenderHistory(
            storyboard_id=sb_id,
            media_asset_id=asset.id,
            label="test",
            youtube_video_id=youtube_video_id,
        )
        db_session.add(rh)
        return rh

    def test_rendered_with_render_history(self, db_session):
        from services.storyboard.crud import _derive_kanban_status

        sb = Storyboard(title="Rendered", group_id=1)
        db_session.add(sb)
        db_session.flush()

        self._create_render_history(db_session, sb.id)
        db_session.commit()
        db_session.refresh(sb)

        result = _derive_kanban_status(sb, image_count=0)
        assert result == "rendered"

    def test_published_with_youtube_id(self, db_session):
        from services.storyboard.crud import _derive_kanban_status

        sb = Storyboard(title="Published", group_id=1)
        db_session.add(sb)
        db_session.flush()

        self._create_render_history(db_session, sb.id, youtube_video_id="abc123")
        db_session.commit()
        db_session.refresh(sb)

        result = _derive_kanban_status(sb, image_count=0)
        assert result == "published"
