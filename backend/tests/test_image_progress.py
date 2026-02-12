"""Test image generation progress tracking and SSE endpoints."""

import pytest

from services.image_progress import (
    ImageGenStage,
    ImageTaskProgress,
    calc_percent,
    create_image_task,
    get_image_task,
)


class TestImageTaskProgress:
    def test_create_task(self):
        task = create_image_task()
        assert task.task_id.startswith("img_")
        assert task.stage == ImageGenStage.QUEUED
        assert task.percent == 0

    def test_get_task(self):
        task = create_image_task()
        found = get_image_task(task.task_id)
        assert found is not None
        assert found.task_id == task.task_id

    def test_get_nonexistent_task(self):
        assert get_image_task("nonexistent") is None

    def test_notify_increments_version(self):
        task = create_image_task()
        v0 = task._version
        task.notify()
        assert task._version == v0 + 1

    @pytest.mark.asyncio
    async def test_wait_for_update_immediate_if_version_changed(self):
        task = create_image_task()
        v0 = task._version
        task.notify()
        result = await task.wait_for_update(v0, timeout=0.1)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_update_timeout(self):
        task = create_image_task()
        v0 = task._version
        result = await task.wait_for_update(v0, timeout=0.1)
        assert result is False


class TestCalcPercent:
    def test_queued_is_zero(self):
        task = ImageTaskProgress(task_id="test1")
        task.stage = ImageGenStage.QUEUED
        assert calc_percent(task) == 0

    def test_composing_is_0(self):
        task = ImageTaskProgress(task_id="test2")
        task.stage = ImageGenStage.COMPOSING
        assert calc_percent(task) == 0  # lo of composing range

    def test_generating_with_progress(self):
        task = ImageTaskProgress(task_id="test3")
        task.stage = ImageGenStage.GENERATING
        task.sd_progress = 0.5
        pct = calc_percent(task)
        # GENERATING range is (10, 85), 50% of 75 span = 37.5 + 10 = 47
        assert pct == 47

    def test_storing_is_85(self):
        task = ImageTaskProgress(task_id="test4")
        task.stage = ImageGenStage.STORING
        assert calc_percent(task) == 85

    def test_completed_is_100(self):
        task = ImageTaskProgress(task_id="test5")
        task.stage = ImageGenStage.COMPLETED
        assert calc_percent(task) == 100


class TestSSEEndpoints:
    """Test the SSE endpoints via TestClient."""

    def test_generate_async_returns_202(self, client):
        """POST /scene/generate-async should return 202 with task_id."""
        from unittest.mock import AsyncMock, patch

        with patch("routers.scene.generate_scene_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"image": "base64data", "images": []}
            resp = client.post(
                "/scene/generate-async",
                json={"prompt": "1girl, standing"},
            )
        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["task_id"].startswith("img_")

    def test_progress_unknown_task_returns_404(self, client):
        """GET /scene/progress/nonexistent should return 404."""
        resp = client.get("/scene/progress/nonexistent")
        assert resp.status_code == 404

    def test_progress_known_task(self, client):
        """GET /scene/progress/{task_id} for a completed task should stream events."""
        task = create_image_task()
        task.stage = ImageGenStage.COMPLETED
        task.percent = 100
        task.result = {"image": "base64", "used_prompt": "test", "warnings": []}

        resp = client.get(f"/scene/progress/{task.task_id}")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        # Should contain at least one SSE data line
        assert "data:" in resp.text
