"""Unit tests for auto-design tool."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.state import StateStore
from sdd_orchestrator.tools.design import (
    _find_task_dir,
    auto_design_task,
    set_state_store,
)


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    return StateStore(db_path=tmp_path / "test_state.db")


@pytest.fixture()
def task_env(tmp_path: Path, store: StateStore):
    """Create a mock task directory structure."""
    current = tmp_path / "current"
    current.mkdir()
    task_dir = current / "SP-099_test-task"
    task_dir.mkdir()
    (task_dir / "spec.md").write_text(
        "# SP-099: Test task\n\npriority: P0\n\n## What\nTest task\n",
        encoding="utf-8",
    )
    # Seed status in DB
    store.set_task_status("SP-099", "pending")
    set_state_store(store)
    yield task_dir, current
    set_state_store(None)


class TestFindTaskDir:
    def test_found(self, task_env):
        task_dir, current = task_env
        with patch("sdd_orchestrator.tools.design.TASKS_CURRENT_DIR", current):
            result = _find_task_dir("SP-099")
            assert result == task_dir

    def test_not_found(self, task_env):
        _, current = task_env
        with patch("sdd_orchestrator.tools.design.TASKS_CURRENT_DIR", current):
            assert _find_task_dir("SP-999") is None

    def test_missing_dir(self, tmp_path):
        with patch("sdd_orchestrator.tools.design.TASKS_CURRENT_DIR", tmp_path / "nonexistent"):
            assert _find_task_dir("SP-099") is None


class TestAutoDesignTask:
    @pytest.fixture()
    def _patch_paths(self, task_env):
        task_dir, current = task_env
        with patch("sdd_orchestrator.tools.design.TASKS_CURRENT_DIR", current):
            yield task_dir

    async def test_skips_non_pending(self, _patch_paths, store):
        store.set_task_status("SP-099", "approved")
        result = await auto_design_task("SP-099")
        assert "not 'pending'" in result

    async def test_skips_existing_design(self, _patch_paths):
        task_dir = _patch_paths
        (task_dir / "design.md").write_text("existing", encoding="utf-8")
        result = await auto_design_task("SP-099")
        assert "already has design.md" in result

    async def test_task_not_found(self, _patch_paths):
        result = await auto_design_task("SP-999")
        assert "not found" in result

    async def test_creates_design_and_auto_approves(self, _patch_paths, store):
        task_dir = _patch_paths
        simple_design = """\
## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `config.py` | 상수 추가 |
| `agents.py` | 함수 추가 |
"""
        with (
            patch(
                "sdd_orchestrator.tools.design.query_agent", new_callable=AsyncMock
            ) as mock_agent,
            patch(
                "sdd_orchestrator.tools.task_utils.git_commit_files", new_callable=AsyncMock
            ) as mock_git,
        ):
            mock_agent.return_value = simple_design
            mock_git.return_value = None

            result = await auto_design_task("SP-099")

        assert "auto-approved" in result
        assert (task_dir / "design.md").exists()
        assert store.get_task_status("SP-099") == "approved"

    async def test_creates_design_but_not_approved(self, _patch_paths, store):
        task_dir = _patch_paths
        blocker_design = """\
## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `config.py` | 상수 추가 |

**BLOCKER**: 사람 승인 필요
"""
        with (
            patch(
                "sdd_orchestrator.tools.design.query_agent", new_callable=AsyncMock
            ) as mock_agent,
            patch(
                "sdd_orchestrator.tools.task_utils.git_commit_files", new_callable=AsyncMock
            ) as mock_git,
        ):
            mock_agent.return_value = blocker_design
            mock_git.return_value = None

            result = await auto_design_task("SP-099")

        assert "not auto-approved" in result
        assert "BLOCKER" in result
        # Status should be 'design' (not approved)
        assert store.get_task_status("SP-099") == "design"

    async def test_timeout_keeps_pending(self, _patch_paths, store):
        async def slow_agent(*args, **kwargs):
            await asyncio.sleep(100)

        with (
            patch("sdd_orchestrator.tools.design.query_agent", side_effect=slow_agent),
            patch("sdd_orchestrator.tools.design.DESIGN_TIMEOUT", 0.01),
        ):
            result = await auto_design_task("SP-099")

        assert "timed out" in result
        # Status should remain pending
        assert store.get_task_status("SP-099") == "pending"
        # No design.md should be created
        task_dir = _patch_paths
        assert not (task_dir / "design.md").exists()
