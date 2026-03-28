"""Unit tests for auto-design tool."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.tools.design import (
    _find_task_dir,
    _read_spec_status,
    _update_spec_status,
    auto_design_task,
)


@pytest.fixture()
def task_env(tmp_path: Path):
    """Create a mock task directory structure."""
    current = tmp_path / "current"
    current.mkdir()
    task_dir = current / "SP-099_test-task"
    task_dir.mkdir()
    (task_dir / "spec.md").write_text(
        "---\nid: SP-099\nstatus: pending\napproved_at:\n---\n## What\nTest task\n",
        encoding="utf-8",
    )
    return task_dir, current


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


class TestReadSpecStatus:
    def test_reads_status(self, task_env):
        task_dir, _ = task_env
        assert _read_spec_status(task_dir) == "pending"

    def test_missing_spec(self, tmp_path):
        assert _read_spec_status(tmp_path) is None


class TestUpdateSpecStatus:
    def test_updates_to_design(self, task_env):
        task_dir, _ = task_env
        _update_spec_status(task_dir, "design")
        assert _read_spec_status(task_dir) == "design"

    def test_updates_to_approved_with_date(self, task_env):
        task_dir, _ = task_env
        _update_spec_status(task_dir, "approved")
        content = (task_dir / "spec.md").read_text(encoding="utf-8")
        assert "status: approved" in content
        assert "approved_at: 20" in content  # Has a date


class TestAutoDesignTask:
    @pytest.fixture()
    def _patch_paths(self, task_env):
        task_dir, current = task_env
        with patch("sdd_orchestrator.tools.design.TASKS_CURRENT_DIR", current):
            yield task_dir

    async def test_skips_non_pending(self, _patch_paths):
        task_dir = _patch_paths
        _update_spec_status(task_dir, "approved")
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

    async def test_creates_design_and_auto_approves(self, _patch_paths):
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
        assert _read_spec_status(task_dir) == "approved"

    async def test_creates_design_but_not_approved(self, _patch_paths):
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
        # Status should remain 'design' (not approved)
        assert _read_spec_status(task_dir) == "design"

    async def test_timeout_keeps_pending(self, _patch_paths):
        task_dir = _patch_paths

        async def slow_agent(*args, **kwargs):
            await asyncio.sleep(100)

        with (
            patch("sdd_orchestrator.tools.design.query_agent", side_effect=slow_agent),
            patch("sdd_orchestrator.tools.design.DESIGN_TIMEOUT", 0.01),
        ):
            result = await auto_design_task("SP-099")

        assert "timed out" in result
        # Status should remain pending
        assert _read_spec_status(task_dir) == "pending"
        # No design.md should be created
        assert not (task_dir / "design.md").exists()
