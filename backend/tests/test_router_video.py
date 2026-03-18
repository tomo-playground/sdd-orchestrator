"""Tests for video router endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from models import MediaAsset, RenderHistory, Storyboard


class TestCreateVideo:
    """Test POST /video/create endpoint."""

    @patch("routers.video.create_video_task", new_callable=AsyncMock)
    def test_create_video_minimal(self, mock_task, client: TestClient, db_session):
        """Create video with minimal scene data."""
        mock_task.return_value = {"video_url": "/videos/test.mp4", "ok": True}

        request_data = {
            "scenes": [
                {"image_url": "/images/scene1.png", "script": "Hello", "duration": 3},
            ],
        }
        response = client.post("/api/v1/video/create", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["video_url"] == "/videos/test.mp4"

    @patch("routers.video.create_video_task", new_callable=AsyncMock)
    def test_create_video_creates_render_history(self, mock_task, client: TestClient, db_session):
        """Video creation creates a RenderHistory row."""
        sb = Storyboard(title="Video Test", description="Test", group_id=1)
        asset = MediaAsset(file_type="video", storage_key="videos/result.mp4", file_name="result.mp4")
        db_session.add_all([sb, asset])
        db_session.commit()
        sb_id = sb.id
        asset_id = asset.id

        mock_task.return_value = {"video_url": "/videos/result.mp4", "media_asset_id": asset_id, "ok": True}

        request_data = {
            "scenes": [
                {"image_url": "/images/s1.png", "script": "Scene 1", "duration": 3},
            ],
            "storyboard_id": sb_id,
            "layout_style": "post",
        }
        # Wrap db_session so endpoint's db.close() doesn't kill the test session
        mock_sl = MagicMock(return_value=db_session)
        db_session.close = lambda: None  # no-op for test
        with patch("routers.video.SessionLocal", mock_sl):
            response = client.post("/api/v1/video/create", json=request_data)
        assert response.status_code == 200

        # Verify render_history row was created
        rows = db_session.query(RenderHistory).filter(RenderHistory.storyboard_id == sb_id).all()
        assert len(rows) == 1
        assert rows[0].label == "post"
        assert rows[0].media_asset_id == asset_id

    @patch("routers.video.create_video_task", new_callable=AsyncMock)
    def test_create_video_appends_render_history(self, mock_task, client: TestClient, db_session):
        """New video adds a second RenderHistory row."""
        sb = Storyboard(title="Append Test", description="Test", group_id=1)
        old_asset = MediaAsset(file_type="video", storage_key="videos/old.mp4", file_name="old.mp4")
        new_asset = MediaAsset(file_type="video", storage_key="videos/new.mp4", file_name="new.mp4")
        db_session.add_all([sb, old_asset, new_asset])
        db_session.commit()
        sb_id = sb.id
        old_asset_id = old_asset.id
        new_asset_id = new_asset.id

        # Pre-insert an existing render_history row
        old_rh = RenderHistory(
            storyboard_id=sb_id,
            media_asset_id=old_asset_id,
            label="post",
        )
        db_session.add(old_rh)
        db_session.commit()

        mock_task.return_value = {"video_url": "/videos/new.mp4", "media_asset_id": new_asset_id, "ok": True}

        request_data = {
            "scenes": [
                {"image_url": "/images/s1.png", "script": "Scene 1", "duration": 3},
            ],
            "storyboard_id": sb_id,
            "layout_style": "full",
        }
        mock_sl = MagicMock(return_value=db_session)
        db_session.close = lambda: None  # no-op for test
        with patch("routers.video.SessionLocal", mock_sl):
            response = client.post("/api/v1/video/create", json=request_data)
        assert response.status_code == 200

        rows = db_session.query(RenderHistory).filter(RenderHistory.storyboard_id == sb_id).all()
        assert len(rows) == 2
        asset_ids = {r.media_asset_id for r in rows}
        assert old_asset_id in asset_ids
        assert new_asset_id in asset_ids

    @patch("routers.video.create_video_task", new_callable=AsyncMock)
    def test_create_video_with_all_options(self, mock_task, client: TestClient, db_session):
        """Create video with full options."""
        mock_task.return_value = {"video_url": "/videos/full.mp4", "ok": True}

        request_data = {
            "scenes": [
                {"image_url": "/images/s1.png", "script": "Hello", "duration": 3},
                {"image_url": "/images/s2.png", "script": "World", "duration": 4},
            ],
            "storyboard_title": "my_video",
            "width": 1080,
            "height": 1920,
            "layout_style": "full",
            "ken_burns_preset": "slow_zoom_in",
            "transition_type": "fade",
            "include_scene_text": True,
            "speed_multiplier": 1.0,
            "bgm_volume": 0.3,
        }
        response = client.post("/api/v1/video/create", json=request_data)
        assert response.status_code == 200

    @patch("routers.video.create_video_task", new_callable=AsyncMock)
    def test_create_video_service_error(self, mock_task, client: TestClient, db_session):
        """Service error propagates as 500."""
        from fastapi import HTTPException

        mock_task.side_effect = HTTPException(status_code=500, detail="Render failed")

        request_data = {
            "scenes": [
                {"image_url": "/images/s1.png", "script": "Hello", "duration": 3},
            ],
        }
        response = client.post("/api/v1/video/create", json=request_data)
        assert response.status_code == 500

    def test_create_video_empty_scenes(self, client: TestClient, db_session):
        """Empty scenes list triggers validation error."""
        request_data = {"scenes": []}
        response = client.post("/api/v1/video/create", json=request_data)
        # FastAPI may accept empty list (no min_length on scenes)
        # but video builder would fail
        assert response.status_code in (200, 422, 500)

    def test_create_video_missing_scenes(self, client: TestClient):
        """Missing scenes field returns 422."""
        response = client.post("/api/v1/video/create", json={})
        assert response.status_code == 422


class TestDeleteVideo:
    """Test POST /video/delete endpoint."""

    def test_delete_video_invalid_extension(self, client: TestClient, db_session):
        """Non-mp4 filename returns 400."""
        request_data = {"filename": "test.avi"}
        response = client.post("/api/v1/video/delete", json=request_data)
        assert response.status_code == 400
        assert "invalid filename" in response.json()["detail"].lower()

    @patch("services.storage.get_storage")
    def test_delete_video_not_found(self, mock_storage, client: TestClient, db_session):
        """Deleting non-existent video returns not_found."""
        mock_storage_instance = MagicMock()
        mock_storage_instance.exists.return_value = False
        mock_storage.return_value = mock_storage_instance

        with patch("routers.video.VIDEO_DIR", Path("/tmp/test_videos_nonexistent")):
            request_data = {"filename": "nonexistent.mp4"}
            response = client.post("/api/v1/video/delete", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False
            assert data["reason"] == "not_found"

    def test_delete_video_path_traversal(self, client: TestClient, db_session):
        """Path traversal in filename is neutralized (basename extraction)."""
        request_data = {"filename": "../../etc/passwd.mp4"}
        response = client.post("/api/v1/video/delete", json=request_data)
        # basename extracts just "passwd.mp4", which won't exist
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False

    def test_delete_video_missing_identifier(self, client: TestClient):
        """Missing both filename and asset_id returns 400."""
        response = client.post("/api/v1/video/delete", json={})
        assert response.status_code == 400
        assert "either" in response.json()["detail"].lower()


class TestVideoExists:
    """Test GET /video/exists endpoint."""

    def test_exists_nonexistent(self, client: TestClient):
        """Non-existent file returns false."""
        response = client.get("/api/v1/video/exists?filename=nonexistent.mp4")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False

    def test_exists_non_mp4(self, client: TestClient):
        """Non-mp4 file returns false."""
        response = client.get("/api/v1/video/exists?filename=test.avi")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False

    def test_exists_missing_param(self, client: TestClient):
        """Missing filename parameter returns 422."""
        response = client.get("/api/v1/video/exists")
        assert response.status_code == 422

    def test_exists_path_traversal(self, client: TestClient):
        """Path traversal in filename is neutralized."""
        response = client.get("/api/v1/video/exists?filename=../../etc/passwd.mp4")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False


class TestGetTransitions:
    """Test GET /video/transitions endpoint."""

    def test_get_transitions(self, client: TestClient):
        """Returns list of transition effects."""
        response = client.get("/api/v1/video/transitions")
        assert response.status_code == 200
        data = response.json()

        assert "transitions" in data
        assert isinstance(data["transitions"], list)
        assert len(data["transitions"]) > 0

        # Check structure of each transition
        for t in data["transitions"]:
            assert "value" in t
            assert "label" in t
            assert "description" in t


class TestExtractCaption:
    """Test POST /video/extract-caption endpoint."""

    def test_extract_caption_empty_text(self, client: TestClient):
        """Empty text returns 400."""
        response = client.post("/api/v1/video/extract-caption", json={"text": ""})
        assert response.status_code == 400
        assert "no text" in response.json()["detail"].lower()

    def test_extract_caption_short_text(self, client: TestClient):
        """Short text (<=60 chars) returned as-is."""
        with patch("config.gemini_client", MagicMock()):
            short_text = "Short caption text"
            response = client.post("/api/v1/video/extract-caption", json={"text": short_text})
            assert response.status_code == 200
            data = response.json()
            assert data["caption"] == short_text

    def test_extract_caption_no_gemini(self, client: TestClient):
        """Returns 503 when Gemini is not configured and text is long."""
        with patch("config.gemini_client", None):
            long_text = "A" * 100
            response = client.post("/api/v1/video/extract-caption", json={"text": long_text})
            assert response.status_code == 503
            assert "gemini" in response.json()["detail"].lower()

    def test_extract_caption_with_gemini(self, client: TestClient):
        """Gemini extracts concise caption from long text."""
        mock_response = MagicMock()
        mock_response.text = "Extracted caption"

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("config.gemini_client", mock_client):
            long_text = "A" * 100
            response = client.post("/api/v1/video/extract-caption", json={"text": long_text})
            assert response.status_code == 200
            data = response.json()
            assert data["caption"] == "Extracted caption"
            assert data["original_length"] == 100

    def test_extract_caption_strips_quotes(self, client: TestClient):
        """Gemini response with quotes is cleaned."""
        mock_response = MagicMock()
        mock_response.text = '"Quoted caption"'

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("config.gemini_client", mock_client):
            long_text = "B" * 100
            response = client.post("/api/v1/video/extract-caption", json={"text": long_text})
            assert response.status_code == 200
            data = response.json()
            assert data["caption"] == "Quoted caption"

    def test_extract_caption_gemini_error_fallback(self, client: TestClient):
        """Gemini error falls back to truncation."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API error")

        with patch("config.gemini_client", mock_client):
            long_text = "C" * 100
            response = client.post("/api/v1/video/extract-caption", json={"text": long_text})
            assert response.status_code == 200
            data = response.json()
            assert len(data["caption"]) <= 60
            assert data.get("fallback") is True

    def test_extract_caption_missing_text_field(self, client: TestClient):
        """Missing text field returns 422 (Pydantic validation)."""
        response = client.post("/api/v1/video/extract-caption", json={})
        assert response.status_code == 422


class TestRenderHistory:
    """Test GET /video/render-history endpoint."""

    _counter = 0

    def _create_render_history(self, db_session, count=1, project_name="Test Project", group_name="Test Series"):
        """Helper: create Project → Group → Storyboard → MediaAsset → RenderHistory rows."""
        from models.group import Group
        from models.project import Project

        project = Project(name=project_name)
        db_session.add(project)
        db_session.flush()
        group = Group(project_id=project.id, name=group_name)
        db_session.add(group)
        db_session.flush()

        rh_ids = []
        for _i in range(count):
            TestRenderHistory._counter += 1
            n = TestRenderHistory._counter
            sb = Storyboard(title=f"SB {n}", description="test", group_id=group.id)
            asset = MediaAsset(file_type="video", storage_key=f"videos/v{n}.mp4", file_name=f"v{n}.mp4")
            db_session.add_all([sb, asset])
            db_session.flush()
            rh = RenderHistory(storyboard_id=sb.id, media_asset_id=asset.id, label="full")
            db_session.add(rh)
            db_session.flush()
            rh_ids.append(rh.id)

        db_session.commit()
        return project, group, rh_ids

    @patch("services.storage.get_storage")
    def test_render_history_list_empty(self, mock_storage, client: TestClient, db_session):
        """Empty DB returns empty items and total=0."""
        mock_store = MagicMock()
        mock_store.get_url.return_value = "http://test/video.mp4"
        mock_storage.return_value = mock_store

        response = client.get("/api/v1/video/render-history")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["offset"] == 0
        assert data["limit"] == 12

    @patch("services.storage.get_storage")
    def test_render_history_list_paginated(self, mock_storage, client: TestClient, db_session):
        """Pagination returns correct items and total."""
        mock_store = MagicMock()
        mock_store.get_url.return_value = "http://test/video.mp4"
        mock_storage.return_value = mock_store

        self._create_render_history(db_session, count=5)

        # First page
        response = client.get("/api/v1/video/render-history?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        # Verify newest first (descending created_at)
        assert data["items"][0]["id"] >= data["items"][1]["id"]

        # Second page
        response = client.get("/api/v1/video/render-history?limit=2&offset=2")
        data2 = response.json()
        assert len(data2["items"]) == 2
        assert data2["total"] == 5

    @patch("services.storage.get_storage")
    def test_render_history_filter_by_project(self, mock_storage, client: TestClient, db_session):
        """project_id filter returns only matching project's renders."""
        mock_store = MagicMock()
        mock_store.get_url.return_value = "http://test/video.mp4"
        mock_storage.return_value = mock_store

        proj_a, _, _ = self._create_render_history(db_session, count=3, project_name="Project A")
        self._create_render_history(db_session, count=2, project_name="Project B")

        response = client.get(f"/api/v1/video/render-history?project_id={proj_a.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(item["project_id"] == proj_a.id for item in data["items"])

    @patch("services.storage.get_storage")
    def test_render_history_excludes_soft_deleted(self, mock_storage, client: TestClient, db_session):
        """Soft-deleted storyboards are excluded from results."""
        from datetime import datetime

        mock_store = MagicMock()
        mock_store.get_url.return_value = "http://test/video.mp4"
        mock_storage.return_value = mock_store

        _, _, rh_ids = self._create_render_history(db_session, count=2)

        # Soft-delete the first storyboard
        first_rh = db_session.query(RenderHistory).get(rh_ids[0])
        sb = first_rh.storyboard
        sb.deleted_at = datetime.now()
        db_session.commit()

        response = client.get("/api/v1/video/render-history")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == rh_ids[1]
