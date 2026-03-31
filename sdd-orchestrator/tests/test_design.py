"""Unit tests for auto-design tool and design retry approval."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.main import OrchestratorDaemon
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


# ── Retry Design Approval Tests ──────────────────────────


# Simple design.md content without BLOCKER (auto-approvable)
_SIMPLE_DESIGN = """\
## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `config.py` | 상수 추가 |
| `agents.py` | 함수 추가 |
"""

# Design with BLOCKER (not auto-approvable)
_BLOCKER_DESIGN = """\
## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `config.py` | 상수 추가 |

**BLOCKER**: 사람 승인 필요
"""


@pytest.fixture()
def daemon(tmp_path: Path) -> OrchestratorDaemon:
    """Minimal daemon for testing retry logic."""
    return OrchestratorDaemon(interval=0, db_path=tmp_path / "test.db")


@pytest.fixture()
def retry_env(tmp_path: Path, daemon: OrchestratorDaemon):
    """Create a task directory with design.md for retry tests."""
    current = tmp_path / "current"
    current.mkdir()
    task_dir = current / "SP-200_retry-test"
    task_dir.mkdir()
    daemon.state.set_task_status("SP-200", "design")
    yield daemon, task_dir, current


class TestRetryDesignApproval:
    """Tests for OrchestratorDaemon._retry_design_approval()."""

    async def test_retry_approves_design_task(self, retry_env):
        """design + no BLOCKER -> approved 전환."""
        daemon, task_dir, current = retry_env
        (task_dir / "design.md").write_text(_SIMPLE_DESIGN, encoding="utf-8")

        with (
            patch("sdd_orchestrator.main.ENABLE_AUTO_DESIGN", True),
            patch("sdd_orchestrator.main.TASKS_CURRENT_DIR", current),
            patch("sdd_orchestrator.main.git_commit_files", new_callable=AsyncMock) as mock_git,
        ):
            mock_git.return_value = None
            await daemon._retry_design_approval()

        assert daemon.state.get_task_status("SP-200") == "approved"
        mock_git.assert_called_once()

    async def test_retry_skips_when_auto_design_disabled(self, retry_env):
        """ENABLE_AUTO_DESIGN=False -> 재평가 스킵."""
        daemon, task_dir, current = retry_env
        (task_dir / "design.md").write_text(_SIMPLE_DESIGN, encoding="utf-8")

        with (
            patch("sdd_orchestrator.main.ENABLE_AUTO_DESIGN", False),
            patch("sdd_orchestrator.main.TASKS_CURRENT_DIR", current),
        ):
            await daemon._retry_design_approval()

        # Status unchanged
        assert daemon.state.get_task_status("SP-200") == "design"

    async def test_retry_skips_no_design_md(self, retry_env):
        """design.md 없음 -> warning + 스킵."""
        daemon, task_dir, current = retry_env
        # No design.md written

        with (
            patch("sdd_orchestrator.main.ENABLE_AUTO_DESIGN", True),
            patch("sdd_orchestrator.main.TASKS_CURRENT_DIR", current),
        ):
            await daemon._retry_design_approval()

        assert daemon.state.get_task_status("SP-200") == "design"

    async def test_retry_respects_max_attempts(self, retry_env):
        """3회 실패 후 can_auto_approve 미호출."""
        daemon, task_dir, current = retry_env
        (task_dir / "design.md").write_text(_BLOCKER_DESIGN, encoding="utf-8")

        # Exhaust 3 attempts
        for _ in range(3):
            daemon.state.increment_approval_attempts("SP-200")

        with (
            patch("sdd_orchestrator.main.ENABLE_AUTO_DESIGN", True),
            patch("sdd_orchestrator.main.TASKS_CURRENT_DIR", current),
            patch("sdd_orchestrator.main.can_auto_approve") as mock_approve,
            patch("sdd_orchestrator.main.do_notify_human", new_callable=AsyncMock),
        ):
            await daemon._retry_design_approval()

        mock_approve.assert_not_called()

    async def test_retry_sends_notification_on_3rd_failure(self, retry_env):
        """3회차 실패 시 do_notify_human 1회 호출."""
        daemon, task_dir, current = retry_env
        (task_dir / "design.md").write_text(_BLOCKER_DESIGN, encoding="utf-8")

        # Already failed 2 times
        daemon.state.increment_approval_attempts("SP-200")
        daemon.state.increment_approval_attempts("SP-200")

        with (
            patch("sdd_orchestrator.main.ENABLE_AUTO_DESIGN", True),
            patch("sdd_orchestrator.main.TASKS_CURRENT_DIR", current),
            patch("sdd_orchestrator.main.do_notify_human", new_callable=AsyncMock) as mock_notify,
        ):
            await daemon._retry_design_approval()

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0][0]
        assert "3회 실패" in call_args["message"]
        assert call_args["level"] == "warning"

    async def test_retry_no_duplicate_notification(self, retry_env):
        """4회차에서 do_notify_human 재호출 안 됨."""
        daemon, task_dir, current = retry_env
        (task_dir / "design.md").write_text(_BLOCKER_DESIGN, encoding="utf-8")

        # Already exhausted 3 attempts
        for _ in range(3):
            daemon.state.increment_approval_attempts("SP-200")

        with (
            patch("sdd_orchestrator.main.ENABLE_AUTO_DESIGN", True),
            patch("sdd_orchestrator.main.TASKS_CURRENT_DIR", current),
            patch("sdd_orchestrator.main.do_notify_human", new_callable=AsyncMock) as mock_notify,
        ):
            await daemon._retry_design_approval()

        mock_notify.assert_not_called()

    def test_approval_attempts_persist(self, tmp_path: Path):
        """SQLite 영속성 — 재연결 후 카운터 유지."""
        db_path = tmp_path / "persist.db"
        store1 = StateStore(db_path=db_path)
        store1.increment_approval_attempts("SP-300")
        store1.increment_approval_attempts("SP-300")
        store1.close()

        store2 = StateStore(db_path=db_path)
        assert store2.get_approval_attempts("SP-300") == 2
        store2.close()
