"""Unit tests for worktree management tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.state import StateStore
from sdd_orchestrator.tools import worktree as worktree_mod
from sdd_orchestrator.tools.worktree import (
    do_check_running_worktrees,
    do_launch_sdd_run,
)


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


class TestHasUncommittedChanges:
    def test_returns_false_when_clean(self):
        with patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            assert worktree_mod._has_uncommitted_changes("/fake/dir") is False

    def test_returns_true_when_modified(self):
        with patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = " M file.py\n"
            assert worktree_mod._has_uncommitted_changes("/fake/dir") is True

    def test_returns_true_when_git_returns_nonzero(self):
        with patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128
            mock_run.return_value.stdout = ""
            assert worktree_mod._has_uncommitted_changes("/fake/dir") is True

    def test_returns_true_on_git_failure(self):
        with patch(
            "sdd_orchestrator.tools.worktree.subprocess.run",
            side_effect=OSError("git not found"),
        ):
            assert worktree_mod._has_uncommitted_changes("/fake/dir") is True


class TestSafeWorktreePath:
    def test_rejects_traversal(self, tmp_path: Path):
        result = worktree_mod._safe_worktree_path("../../etc/passwd", tmp_path)
        assert result is None

    def test_rejects_absolute_path(self, tmp_path: Path):
        result = worktree_mod._safe_worktree_path("/etc/passwd", tmp_path)
        assert result is None

    def test_accepts_valid_task_id(self, tmp_path: Path):
        result = worktree_mod._safe_worktree_path("SP-099", tmp_path)
        assert result == (tmp_path / ".claude/worktrees/SP-099").resolve()


class TestCleanupWorktree:
    def test_cleanup_removes_worktree(self, tmp_path: Path):
        wt_dir = tmp_path / ".claude/worktrees/SP-099"
        wt_dir.mkdir(parents=True)
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch.object(worktree_mod, "_has_uncommitted_changes", return_value=False),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            worktree_mod._cleanup_worktree("SP-099")
            mock_run.assert_called_once()
            assert "--force" in mock_run.call_args[0][0]

    def test_cleanup_skips_when_uncommitted(self, tmp_path: Path):
        wt_dir = tmp_path / ".claude/worktrees/SP-099"
        wt_dir.mkdir(parents=True)
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch.object(worktree_mod, "_has_uncommitted_changes", return_value=True),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            worktree_mod._cleanup_worktree("SP-099")
            mock_run.assert_not_called()

    def test_cleanup_skips_when_dir_not_exists(self, tmp_path: Path):
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            worktree_mod._cleanup_worktree("SP-099")
            mock_run.assert_not_called()

    def test_cleanup_logs_warning_on_failure(self, tmp_path: Path):
        wt_dir = tmp_path / ".claude/worktrees/SP-099"
        wt_dir.mkdir(parents=True)
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch.object(worktree_mod, "_has_uncommitted_changes", return_value=False),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "lock error"
            # Should not raise
            worktree_mod._cleanup_worktree("SP-099")


class TestRemoveStaleWorktree:
    def test_removes_existing_stale_worktree(self, tmp_path: Path):
        wt_dir = tmp_path / ".claude/worktrees/SP-099"
        wt_dir.mkdir(parents=True)
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch.object(worktree_mod, "_has_uncommitted_changes", return_value=False),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            worktree_mod._remove_stale_worktree("SP-099")
            # prune + remove = 2 calls
            assert mock_run.call_count == 2

    def test_skips_when_no_worktree(self, tmp_path: Path):
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            worktree_mod._remove_stale_worktree("SP-099")
            mock_run.assert_not_called()

    def test_skips_when_uncommitted(self, tmp_path: Path):
        wt_dir = tmp_path / ".claude/worktrees/SP-099"
        wt_dir.mkdir(parents=True)
        with (
            patch("sdd_orchestrator.config.PROJECT_ROOT", tmp_path),
            patch.object(worktree_mod, "_has_uncommitted_changes", return_value=True),
            patch("sdd_orchestrator.tools.worktree.subprocess.run") as mock_run,
        ):
            worktree_mod._remove_stale_worktree("SP-099")
            mock_run.assert_not_called()


class TestWatchProcessCleanup:
    @pytest.mark.asyncio
    async def test_watch_calls_cleanup_on_success(self, store: StateStore):
        run_id = store.start_run("SP-099", pid=999)
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=0)

        with patch.object(worktree_mod, "_cleanup_worktree") as mock_cleanup:
            await worktree_mod._watch_process(mock_proc, "SP-099", run_id)
            mock_cleanup.assert_called_once_with("SP-099")

    @pytest.mark.asyncio
    async def test_watch_calls_cleanup_on_failure(self, store: StateStore):
        run_id = store.start_run("SP-099", pid=999)
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=1)

        with patch.object(worktree_mod, "_cleanup_worktree") as mock_cleanup:
            await worktree_mod._watch_process(mock_proc, "SP-099", run_id)
            mock_cleanup.assert_called_once_with("SP-099")

    @pytest.mark.asyncio
    async def test_watch_calls_cleanup_on_exception(self, store: StateStore):
        run_id = store.start_run("SP-099", pid=999)
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(side_effect=RuntimeError("test"))

        with patch.object(worktree_mod, "_cleanup_worktree") as mock_cleanup:
            await worktree_mod._watch_process(mock_proc, "SP-099", run_id)
            mock_cleanup.assert_called_once_with("SP-099")


class TestLaunchWithStaleWorktree:
    @pytest.mark.asyncio
    async def test_launch_removes_stale_before_create(self, store: StateStore):
        mock_proc = AsyncMock()
        mock_proc.pid = 12345
        mock_proc.wait = AsyncMock(return_value=0)

        with (
            patch("sdd_orchestrator.tools.worktree.asyncio.create_subprocess_exec") as mock_exec,
            patch.object(worktree_mod, "_remove_stale_worktree") as mock_remove,
        ):
            mock_exec.return_value = mock_proc
            result = await do_launch_sdd_run("SP-099")

        assert "isError" not in result
        mock_remove.assert_called_once_with("SP-099")
