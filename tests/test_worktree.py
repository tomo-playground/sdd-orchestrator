"""Unit tests for worktree management tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.state import StateStore
from sdd_orchestrator.tools import worktree as worktree_mod
from sdd_orchestrator.tools.worktree import do_check_running_worktrees, do_launch_sdd_run


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

        with patch("sdd_orchestrator.tools.worktree.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc
            result = await do_launch_sdd_run("SP-099")

        assert "isError" not in result
        assert "SP-099" in result["content"][0]["text"]
        assert len(store.get_running_runs()) == 1

    @pytest.mark.asyncio
    async def test_launch_blocks_over_max_parallel(self, store: StateStore):
        with patch("sdd_orchestrator.tools.worktree.MAX_PARALLEL_RUNS", 1):
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
            "sdd_orchestrator.tools.worktree.asyncio.create_subprocess_exec",
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

        with patch.object(worktree_mod, "_is_pid_alive", return_value=True):
            result = await do_check_running_worktrees()
        text = result["content"][0]["text"]
        assert "SP-001" in text
        assert "SP-002" in text

    @pytest.mark.asyncio
    async def test_excludes_finished(self, store: StateStore):
        rid = store.start_run("SP-001", pid=111)
        store.finish_run(rid, exit_code=0)
        store.start_run("SP-002", pid=222)

        with patch.object(worktree_mod, "_is_pid_alive", return_value=True):
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


def _make_gh_output(prs: list[dict]) -> str:
    """Helper: build fake gh pr list JSON output."""
    import json

    return json.dumps(prs)


class TestHasOpenPr:
    """Tests for _has_open_pr exact matching logic."""

    def test_no_match_when_different_task_pr_exists(self):
        """SP-117 must NOT match feat/SP-111-e2e-docker-ci."""
        gh_output = _make_gh_output([{"number": 283, "headRefName": "feat/SP-111-e2e-docker-ci"}])
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = gh_output
            result = worktree_mod._has_open_pr("SP-117")
        assert result is None

    def test_match_when_exact_task_pr_exists(self):
        """SP-117 must match feat/SP-117-some-feature."""
        gh_output = _make_gh_output([{"number": 300, "headRefName": "feat/SP-117-some-feature"}])
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = gh_output
            result = worktree_mod._has_open_pr("SP-117")
        assert result == "PR #300"

    def test_no_match_when_no_prs(self):
        """Empty PR list → None."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "[]"
            result = worktree_mod._has_open_pr("SP-117")
        assert result is None

    def test_no_match_when_branch_has_no_sp_number(self):
        """PR with branch lacking SP-NNN → ignored."""
        gh_output = _make_gh_output([{"number": 100, "headRefName": "fix/typo-readme"}])
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = gh_output
            result = worktree_mod._has_open_pr("SP-117")
        assert result is None

    def test_returns_first_matching_pr(self):
        """Multiple PRs for same task → return first."""
        gh_output = _make_gh_output(
            [
                {"number": 200, "headRefName": "feat/SP-050-first"},
                {"number": 201, "headRefName": "fix/SP-050-second"},
            ]
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = gh_output
            result = worktree_mod._has_open_pr("SP-050")
        assert result == "PR #200"

    def test_no_match_partial_number_overlap(self):
        """SP-11 must NOT match feat/SP-111-xxx (prefix overlap)."""
        gh_output = _make_gh_output([{"number": 500, "headRefName": "feat/SP-111-feature"}])
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = gh_output
            result = worktree_mod._has_open_pr("SP-11")
        assert result is None

    def test_gh_failure_returns_none(self):
        """gh command failure → None (graceful)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            result = worktree_mod._has_open_pr("SP-117")
        assert result is None
