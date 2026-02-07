"""Tests for video render progress tracking (SSE infrastructure)."""

import asyncio
import time
from unittest.mock import patch

import pytest

from services.video.progress import (
    RenderStage,
    TaskProgress,
    _tasks,
    calc_overall_percent,
    create_task,
    get_task,
)


@pytest.fixture(autouse=True)
def _clear_tasks():
    """Ensure task store is clean before/after each test."""
    _tasks.clear()
    yield
    _tasks.clear()


class TestCreateTask:
    def test_returns_task_progress(self):
        task = create_task(total_scenes=5)
        assert isinstance(task, TaskProgress)
        assert task.total_scenes == 5
        assert task.stage == RenderStage.QUEUED
        assert task.percent == 0
        assert len(task.task_id) == 12

    def test_task_stored_in_memory(self):
        task = create_task(total_scenes=3)
        assert task.task_id in _tasks

    def test_unique_task_ids(self):
        t1 = create_task(total_scenes=1)
        t2 = create_task(total_scenes=1)
        assert t1.task_id != t2.task_id


class TestGetTask:
    def test_returns_existing_task(self):
        task = create_task(total_scenes=2)
        found = get_task(task.task_id)
        assert found is task

    def test_returns_none_for_unknown_id(self):
        assert get_task("nonexistent") is None

    def test_returns_none_for_expired_task(self):
        task = create_task(total_scenes=1)
        task.created_at = time.time() - 99999
        assert get_task(task.task_id) is None
        assert task.task_id not in _tasks


class TestCalcOverallPercent:
    def test_queued_is_zero(self):
        task = TaskProgress(task_id="t1", stage=RenderStage.QUEUED, total_scenes=5)
        assert calc_overall_percent(task) == 0

    def test_setup_avatars(self):
        task = TaskProgress(task_id="t1", stage=RenderStage.SETUP_AVATARS)
        assert calc_overall_percent(task) == 0  # lo of range

    def test_process_scenes_fraction(self):
        task = TaskProgress(
            task_id="t1",
            stage=RenderStage.PROCESS_SCENES,
            total_scenes=4,
            current_scene=3,  # (3-1)/4 = 0.5 of range 2..52 → 2+25=27
        )
        assert calc_overall_percent(task) == 27

    def test_encode_percent(self):
        task = TaskProgress(
            task_id="t1",
            stage=RenderStage.ENCODE,
            encode_percent=50,  # 50% of range 65..95 → 65+15=80
        )
        assert calc_overall_percent(task) == 80

    def test_completed_is_100(self):
        task = TaskProgress(task_id="t1", stage=RenderStage.COMPLETED)
        assert calc_overall_percent(task) == 100


class TestTaskNotify:
    def test_notify_increments_version(self):
        task = create_task(total_scenes=1)
        assert task._version == 0
        task.notify()
        assert task._version == 1
        assert task._event.is_set()
        task.notify()
        assert task._version == 2

    @pytest.mark.asyncio
    async def test_wait_for_update_receives_notify(self):
        task = create_task(total_scenes=1)
        version = task._version

        async def _notify_later():
            await asyncio.sleep(0.05)
            task.notify()

        asyncio.create_task(_notify_later())
        updated = await task.wait_for_update(version, timeout=2.0)
        assert updated is True

    @pytest.mark.asyncio
    async def test_wait_for_update_times_out(self):
        task = create_task(total_scenes=1)
        updated = await task.wait_for_update(task._version, timeout=0.05)
        assert updated is False

    @pytest.mark.asyncio
    async def test_wait_for_update_already_changed(self):
        """If version already changed, wait_for_update returns immediately."""
        task = create_task(total_scenes=1)
        task.notify()  # version=1
        updated = await task.wait_for_update(0, timeout=0.01)
        assert updated is True


class TestCleanupExpired:
    @patch("services.video.progress._get_ttl", return_value=1)
    def test_cleanup_removes_old_tasks(self, _mock_ttl):
        t1 = create_task(total_scenes=1)
        t1.created_at = time.time() - 10  # Expired
        # Creating a new task triggers cleanup
        t2 = create_task(total_scenes=1)
        assert t1.task_id not in _tasks
        assert t2.task_id in _tasks
