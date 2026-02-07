"""Tests for async video creation and SSE progress endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.video.progress import _tasks


class TestCreateVideoAsync:
    """Test POST /video/create-async endpoint."""

    @patch("routers.video.VideoBuilder")
    def test_returns_202_with_task_id(self, mock_builder_cls, client: TestClient, db_session):
        """Async create returns 202 with a task_id."""
        mock_builder = mock_builder_cls.return_value
        mock_builder.build = AsyncMock(return_value={"video_url": "/videos/test.mp4"})

        request_data = {
            "scenes": [
                {"image_url": "/images/s1.png", "script": "Hello", "duration": 3},
            ],
        }
        response = client.post("/video/create-async", json=request_data)
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) == 12

    def test_missing_scenes_returns_422(self, client: TestClient):
        """Missing scenes field returns 422."""
        response = client.post("/video/create-async", json={})
        assert response.status_code == 422

    def test_task_created_in_store(self, client: TestClient, db_session):
        """Task is registered in the in-memory store."""
        _tasks.clear()

        with patch("routers.video.VideoBuilder") as mock_cls:
            mock_cls.return_value.build = AsyncMock(return_value={"video_url": "/v.mp4"})
            request_data = {
                "scenes": [{"image_url": "/img.png", "script": "Hi", "duration": 2}],
            }
            response = client.post("/video/create-async", json=request_data)
            task_id = response.json()["task_id"]
            assert task_id in _tasks

        _tasks.clear()


class TestStreamProgress:
    """Test GET /video/progress/{task_id} endpoint."""

    def test_unknown_task_returns_404(self, client: TestClient):
        """Non-existent task_id returns 404."""
        response = client.get("/video/progress/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
