"""Unit tests for worktree management tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from orchestrator.state import StateStore
from orchestrator.tools import worktree as worktree_mod
from orchestrator.tools.worktree import do_check_running_worktrees, do_launch_sdd_run


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    """Create a StateStore with a temporary database."""
    return StateStore(db_path=tmp_path / "test_state.db")


@pytest.fixture(autouse=True)
def _inject_store(store: StateStore):
    """Inject test store into worktree module."""
    worktree_mod.set_state_store(store)
    yield
    worktree_mod.set_state_store(None)


class TestLaunchSddRun:
    @pytest.mark.asyncio
    async def test_launch_success(self, store: StateStore):
        mock_proc = AsyncMock()
        mock_proc.pid = 12345
        mock_proc.wait = AsyncMock(return_value=0)

        with patch("orchestrator.tools.worktree.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc
            result = await do_launch_sdd_run("SP-099")

        assert "isError" not in result
        assert "SP-099" in result["content"][0]["text"]
        assert len(store.get_running_runs()) == 1

    @pytest.mark.asyncio
    async def test_launch_blocks_over_max_parallel(self, store: StateStore):
        with patch("orchestrator.tools.worktree.MAX_PARALLEL_RUNS", 1):
            store.start_run("SP-001", pid=111)
            result = await do_launch_sdd_run("SP-002")

        assert result.get("isError") is True
        assert "Parallel limit" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_launch_blocks_duplicate(self, store: StateStore):
        store.start_run("SP-099", pid=111)
        result = await do_launch_sdd_run("SP-099")

        assert result.get("isError") is True
        assert "already running" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_launch_blocks_after_3_failures(self, store: StateStore):
        for _ in range(3):
            rid = store.start_run("SP-099", pid=111)
            store.finish_run(rid, exit_code=1)

        result = await do_launch_sdd_run("SP-099")

        assert result.get("isError") is True
        assert "blocked" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_launch_without_state_store(self):
        worktree_mod.set_state_store(None)
        result = await do_launch_sdd_run("SP-099")
        assert result.get("isError") is True

    @pytest.mark.asyncio
    async def test_claude_not_found(self):
        with patch(
            "orchestrator.tools.worktree.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError,
        ):
            result = await do_launch_sdd_run("SP-099")

        assert result.get("isError") is True
        assert "not found" in result["content"][0]["text"]


class TestCheckRunningWorktrees:
    @pytest.mark.asyncio
    async def test_empty(self):
        result = await do_check_running_worktrees()
        assert "[]" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_with_running(self, store: StateStore):
        store.start_run("SP-001", pid=111)
        store.start_run("SP-002", pid=222)

        result = await do_check_running_worktrees()
        text = result["content"][0]["text"]
        assert "SP-001" in text
        assert "SP-002" in text

    @pytest.mark.asyncio
    async def test_excludes_finished(self, store: StateStore):
        rid = store.start_run("SP-001", pid=111)
        store.finish_run(rid, exit_code=0)
        store.start_run("SP-002", pid=222)

        result = await do_check_running_worktrees()
        text = result["content"][0]["text"]
        assert "SP-001" not in text
        assert "SP-002" in text


class TestWatchProcess:
    @pytest.mark.asyncio
    async def test_watch_updates_state_on_exit(self, store: StateStore):
        run_id = store.start_run("SP-099", pid=999)
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=0)

        await worktree_mod._watch_process(mock_proc, "SP-099", run_id)

        run = store.get_run_by_task("SP-099")
        assert run["status"] == "success"
        assert run["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_watch_records_failure(self, store: StateStore):
        run_id = store.start_run("SP-099", pid=999)
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=2)

        await worktree_mod._watch_process(mock_proc, "SP-099", run_id)

        run = store.get_run_by_task("SP-099")
        assert run["status"] == "failed"
        assert run["exit_code"] == 2
