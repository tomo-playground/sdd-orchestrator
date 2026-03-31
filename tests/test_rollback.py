"""Unit tests for post-merge rollback monitoring."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.state import StateStore
from sdd_orchestrator.tools.rollback import (
    _check_surge,
    _create_revert_pr,
    _handle_surge,
    _monitor_loop,
    start_post_merge_monitor,
)

# ── _check_surge (pure function) ─────────────────────────


class TestCheckSurge:
    def test_surge_above_threshold(self):
        baseline = {"backend": 2, "frontend": 1, "audio": 1}
        current = {"backend": 5, "frontend": 3, "audio": 1}
        with patch("sdd_orchestrator.tools.rollback.ROLLBACK_ERROR_THRESHOLD", 5):
            is_surge, delta = _check_surge(baseline, current)
        assert is_surge is True
        assert delta == 5

    def test_no_surge_below_threshold(self):
        baseline = {"backend": 2, "frontend": 1, "audio": 1}
        current = {"backend": 4, "frontend": 2, "audio": 1}
        with patch("sdd_orchestrator.tools.rollback.ROLLBACK_ERROR_THRESHOLD", 5):
            is_surge, delta = _check_surge(baseline, current)
        assert is_surge is False
        assert delta == 3

    def test_exact_threshold(self):
        baseline = {"backend": 0}
        current = {"backend": 5}
        with patch("sdd_orchestrator.tools.rollback.ROLLBACK_ERROR_THRESHOLD", 5):
            is_surge, delta = _check_surge(baseline, current)
        assert is_surge is True
        assert delta == 5

    def test_below_threshold_by_one(self):
        baseline = {"backend": 0}
        current = {"backend": 4}
        with patch("sdd_orchestrator.tools.rollback.ROLLBACK_ERROR_THRESHOLD", 5):
            is_surge, delta = _check_surge(baseline, current)
        assert is_surge is False
        assert delta == 4

    def test_negative_delta(self):
        baseline = {"backend": 5}
        current = {"backend": 2}
        with patch("sdd_orchestrator.tools.rollback.ROLLBACK_ERROR_THRESHOLD", 5):
            is_surge, delta = _check_surge(baseline, current)
        assert is_surge is False
        assert delta == -3


# ── StateStore rollback methods ──────────────────────────


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    return StateStore(db_path=tmp_path / "test.db")


class TestStateStoreRollbacks:
    def test_rollbacks_table_created(self, store: StateStore):
        tables = store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert "rollbacks" in [t["name"] for t in tables]

    def test_record_rollback(self, store: StateStore):
        rb_id = store.record_rollback(42, error_count=10, baseline_count=3)
        assert rb_id is not None
        assert rb_id >= 1

        row = store.conn.execute("SELECT * FROM rollbacks WHERE id = ?", (rb_id,)).fetchone()
        assert row["original_pr"] == 42
        assert row["error_count"] == 10
        assert row["baseline_count"] == 3
        assert row["status"] == "monitoring"
        assert row["revert_pr"] is None

    def test_record_rollback_duplicate_returns_none(self, store: StateStore):
        rb_id1 = store.record_rollback(42, error_count=10, baseline_count=3)
        assert rb_id1 is not None
        rb_id2 = store.record_rollback(42, error_count=20, baseline_count=5)
        assert rb_id2 is None

    def test_update_rollback_baseline(self, store: StateStore):
        rb_id = store.record_rollback(42, error_count=0, baseline_count=0)
        assert rb_id is not None
        store.update_rollback_baseline(rb_id, 15)
        row = store.conn.execute("SELECT * FROM rollbacks WHERE id = ?", (rb_id,)).fetchone()
        assert row["baseline_count"] == 15

    def test_update_rollback_surge(self, store: StateStore):
        rb_id = store.record_rollback(42, error_count=0, baseline_count=5)
        assert rb_id is not None
        store.update_rollback_surge(rb_id, 25)
        row = store.conn.execute("SELECT * FROM rollbacks WHERE id = ?", (rb_id,)).fetchone()
        assert row["error_count"] == 25
        assert row["status"] == "surge_detected"
        # finished_at is NOT set here — surge_detected is intermediate, not terminal
        assert row["finished_at"] is None

    def test_update_rollback_status(self, store: StateStore):
        rb_id = store.record_rollback(42, error_count=10, baseline_count=3)
        store.update_rollback_status(rb_id, "reverted", revert_pr=43)

        row = store.conn.execute("SELECT * FROM rollbacks WHERE id = ?", (rb_id,)).fetchone()
        assert row["status"] == "reverted"
        assert row["revert_pr"] == 43
        assert row["finished_at"] is not None

    def test_has_rollback(self, store: StateStore):
        assert store.has_rollback(42) is False
        store.record_rollback(42, error_count=10, baseline_count=3)
        assert store.has_rollback(42) is True
        assert store.has_rollback(99) is False

    def test_get_recent_rollbacks(self, store: StateStore):
        store.record_rollback(10, error_count=5, baseline_count=1)
        store.record_rollback(20, error_count=8, baseline_count=2)

        recent = store.get_recent_rollbacks(hours=24)
        assert len(recent) == 2


# ── _monitor_loop (integration-style, heavy mocking) ─────


class TestMonitorLoop:
    @pytest.mark.asyncio
    async def test_no_surge_completes(self, store: StateStore):
        """Monitor completes after all checks with no surge."""
        baseline = {"backend": 2, "frontend": 1, "audio": 0}
        current = {"backend": 2, "frontend": 1, "audio": 0}

        mock_client = AsyncMock()

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_CHECK_INTERVAL", 1),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_MONITOR_DURATION", 1),
            patch(
                "sdd_orchestrator.tools.sentry.fetch_error_counts",
                new_callable=AsyncMock,
                side_effect=[baseline, current],
            ),
            patch(
                "sdd_orchestrator.tools.sentry.build_sentry_client",
                return_value=mock_client,
            ),
            patch(
                "sdd_orchestrator.tools.rollback._handle_surge", new_callable=AsyncMock
            ) as mock_surge,
            patch("sdd_orchestrator.tools.rollback.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            await _monitor_loop(100, "abc123")

        mock_surge.assert_not_called()
        assert store.has_rollback(100)

    @pytest.mark.asyncio
    async def test_surge_triggers_handle(self, store: StateStore):
        """Monitor detects surge and calls _handle_surge."""
        baseline = {"backend": 0, "frontend": 0, "audio": 0}
        surge = {"backend": 5, "frontend": 3, "audio": 0}

        mock_client = AsyncMock()

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_CHECK_INTERVAL", 1),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_MONITOR_DURATION", 1),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_ERROR_THRESHOLD", 5),
            patch(
                "sdd_orchestrator.tools.sentry.fetch_error_counts",
                new_callable=AsyncMock,
                side_effect=[baseline, surge],
            ),
            patch(
                "sdd_orchestrator.tools.sentry.build_sentry_client",
                return_value=mock_client,
            ),
            patch(
                "sdd_orchestrator.tools.rollback._handle_surge", new_callable=AsyncMock
            ) as mock_surge,
            patch("sdd_orchestrator.tools.rollback.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            await _monitor_loop(101, "def456")

        mock_surge.assert_called_once()
        args = mock_surge.call_args[0]
        assert args[0] == 101  # pr_number
        assert args[1] == "def456"  # merge_sha
        assert args[2] == 8  # delta

    @pytest.mark.asyncio
    async def test_duplicate_rollback_skipped(self, store: StateStore):
        """Monitor skips if rollback already exists for PR."""
        store.record_rollback(200, error_count=5, baseline_count=0)

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch(
                "sdd_orchestrator.tools.sentry.fetch_error_counts",
                new_callable=AsyncMock,
            ) as mock_fetch,
        ):
            await _monitor_loop(200, "xyz789")

        # Should not fetch error counts since it exits early
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancelled_marks_status(self, store: StateStore):
        """Monitor marks cancelled on CancelledError."""
        baseline = {"backend": 0, "frontend": 0, "audio": 0}
        mock_client = AsyncMock()

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_CHECK_INTERVAL", 1),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_MONITOR_DURATION", 1),
            patch(
                "sdd_orchestrator.tools.sentry.fetch_error_counts",
                new_callable=AsyncMock,
                side_effect=[baseline, asyncio.CancelledError()],
            ),
            patch(
                "sdd_orchestrator.tools.sentry.build_sentry_client",
                return_value=mock_client,
            ),
            patch("sdd_orchestrator.tools.rollback.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(asyncio.CancelledError):
                await _monitor_loop(400, "abc123")

        row = store.conn.execute("SELECT * FROM rollbacks WHERE original_pr = ?", (400,)).fetchone()
        assert row["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_exception_marks_monitor_failed(self, store: StateStore):
        """Monitor marks monitor_failed on unexpected Exception."""
        mock_client = AsyncMock()

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_CHECK_INTERVAL", 1),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_MONITOR_DURATION", 1),
            patch(
                "sdd_orchestrator.tools.sentry.fetch_error_counts",
                new_callable=AsyncMock,
                side_effect=RuntimeError("unexpected"),
            ),
            patch(
                "sdd_orchestrator.tools.sentry.build_sentry_client",
                return_value=mock_client,
            ),
            patch("sdd_orchestrator.tools.rollback.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            await _monitor_loop(401, "def456")

        row = store.conn.execute("SELECT * FROM rollbacks WHERE original_pr = ?", (401,)).fetchone()
        assert row["status"] == "monitor_failed"

    @pytest.mark.asyncio
    async def test_fetch_failures_mark_monitor_failed(self, store: StateStore):
        """Monitor marks monitor_failed after consecutive Sentry fetch failures."""
        baseline = {"backend": 0, "frontend": 0, "audio": 0}
        mock_client = AsyncMock()

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_CHECK_INTERVAL", 1),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_MONITOR_DURATION", 10),
            patch("sdd_orchestrator.tools.rollback.ROLLBACK_MAX_FETCH_FAILURES", 3),
            patch(
                "sdd_orchestrator.tools.sentry.fetch_error_counts",
                new_callable=AsyncMock,
                side_effect=[baseline, Exception("fail"), Exception("fail"), Exception("fail")],
            ),
            patch(
                "sdd_orchestrator.tools.sentry.build_sentry_client",
                return_value=mock_client,
            ),
            patch("sdd_orchestrator.tools.rollback.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            await _monitor_loop(300, "abc123")

        assert store.has_rollback(300)
        row = store.conn.execute("SELECT * FROM rollbacks WHERE original_pr = ?", (300,)).fetchone()
        assert row["status"] == "monitor_failed"


# ── _handle_surge ─────────────────────────────────────────


class TestHandleSurge:
    @pytest.mark.asyncio
    async def test_revert_success(self, store: StateStore):
        rb_id = store.record_rollback(50, error_count=10, baseline_count=2)

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch(
                "sdd_orchestrator.tools.rollback._create_revert_pr",
                new_callable=AsyncMock,
                return_value=51,
            ),
            patch(
                "sdd_orchestrator.tools.notify.do_notify_human",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            await _handle_surge(50, "abc123", 8, rb_id)

        row = store.conn.execute("SELECT * FROM rollbacks WHERE id = ?", (rb_id,)).fetchone()
        assert row["status"] == "reverted"
        assert row["revert_pr"] == 51
        mock_notify.assert_called_once()
        msg = mock_notify.call_args[0][0]["message"]
        assert "ROLLBACK" in msg
        assert "revert PR #51" in msg

    @pytest.mark.asyncio
    async def test_revert_failure(self, store: StateStore):
        rb_id = store.record_rollback(60, error_count=10, baseline_count=2)

        with (
            patch("sdd_orchestrator.tools.rollback._get_state_store", return_value=store),
            patch(
                "sdd_orchestrator.tools.rollback._create_revert_pr",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "sdd_orchestrator.tools.notify.do_notify_human",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            await _handle_surge(60, "abc123", 8, rb_id)

        row = store.conn.execute("SELECT * FROM rollbacks WHERE id = ?", (rb_id,)).fetchone()
        assert row["status"] == "revert_failed"
        mock_notify.assert_called_once()
        msg = mock_notify.call_args[0][0]["message"]
        assert "실패" in msg


# ── _create_revert_pr ─────────────────────────────────────


class TestCreateRevertPr:
    @pytest.mark.asyncio
    async def test_success(self):
        with (
            patch(
                "sdd_orchestrator.tools.rollback._get_pr_title",
                new_callable=AsyncMock,
                return_value="Add feature X",
            ),
            patch(
                "sdd_orchestrator.tools.rollback._ensure_label",
                new_callable=AsyncMock,
            ),
            patch(
                "sdd_orchestrator.tools.rollback._run_cmd",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "sdd_orchestrator.tools.rollback._run_cmd_output",
                new_callable=AsyncMock,
                return_value="https://github.com/tomo-playground/shorts-producer/pull/99",
            ),
        ):
            result = await _create_revert_pr(42, "abc123def")

        assert result == 99

    @pytest.mark.asyncio
    async def test_clone_failure(self):
        with (
            patch(
                "sdd_orchestrator.tools.rollback._get_pr_title",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "sdd_orchestrator.tools.rollback._ensure_label",
                new_callable=AsyncMock,
            ),
            patch(
                "sdd_orchestrator.tools.rollback._run_cmd",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            result = await _create_revert_pr(42, "abc123def")

        assert result is None

    @pytest.mark.asyncio
    async def test_revert_conflict(self):
        """git revert fails (merge conflict)."""
        call_count = 0

        async def mock_run_cmd(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # clone succeeds, checkout succeeds, revert fails
            if "revert" in cmd:
                return False
            return True

        with (
            patch(
                "sdd_orchestrator.tools.rollback._get_pr_title",
                new_callable=AsyncMock,
                return_value="Feat",
            ),
            patch(
                "sdd_orchestrator.tools.rollback._ensure_label",
                new_callable=AsyncMock,
            ),
            patch(
                "sdd_orchestrator.tools.rollback._run_cmd",
                side_effect=mock_run_cmd,
            ),
        ):
            result = await _create_revert_pr(42, "abc123def")

        assert result is None


# ── start_post_merge_monitor ──────────────────────────────


class TestStartPostMergeMonitor:
    @pytest.mark.asyncio
    async def test_creates_task(self):
        with patch(
            "sdd_orchestrator.tools.rollback._monitor_loop",
            new_callable=AsyncMock,
        ):
            start_post_merge_monitor(42, "abc123")

        # Task was created (may have already completed due to mocking)
        # Just verify no exception was raised
        assert True


# ── do_merge_pr auto-rollback guard ─────────────────────


class TestMergePrAutoRollbackGuard:
    @pytest.mark.asyncio
    async def test_blocks_auto_rollback_pr(self):
        from sdd_orchestrator.tools.github import do_merge_pr

        pr_data = {
            "number": 99,
            "title": "Revert PR #42",
            "headRefName": "revert/PR-42",
            "state": "OPEN",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
            "labels": [{"name": "auto-rollback"}],
        }

        with patch(
            "sdd_orchestrator.tools.github._run_gh_command",
            new_callable=AsyncMock,
            return_value={"data": pr_data},
        ):
            result = await do_merge_pr(99)

        assert result.get("isError") is True
        assert "auto-rollback" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_skips_monitor_when_sentry_token_empty(self):
        from sdd_orchestrator.tools.github import do_merge_pr

        pr_data = {
            "number": 55,
            "title": "Minor fix",
            "headRefName": "fix/SP-055",
            "state": "OPEN",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
            "labels": [],
        }
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch(
                "sdd_orchestrator.tools.github._run_gh_command",
                new_callable=AsyncMock,
                return_value={"data": pr_data},
            ),
            patch(
                "sdd_orchestrator.tools.github.asyncio.create_subprocess_exec", return_value=mock_proc
            ),
            patch("sdd_orchestrator.tools.github.asyncio.wait_for", return_value=(b"", b"")),
            patch("sdd_orchestrator.rules.can_auto_merge", return_value=(True, "")),
            patch("sdd_orchestrator.tools.rollback.start_post_merge_monitor") as mock_monitor,
            patch("sdd_orchestrator.config.SENTRY_AUTH_TOKEN", ""),
        ):
            result = await do_merge_pr(55)

        assert not result.get("isError", False)
        mock_monitor.assert_not_called()

    @pytest.mark.asyncio
    async def test_starts_monitor_after_merge(self):
        from sdd_orchestrator.tools.github import do_merge_pr

        pr_data = {
            "number": 50,
            "title": "Add feature",
            "headRefName": "feat/SP-050",
            "state": "OPEN",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
            "labels": [],
        }
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch(
                "sdd_orchestrator.tools.github._run_gh_command",
                new_callable=AsyncMock,
                side_effect=[
                    {"data": pr_data},  # pr view for merge check
                    {"data": {"mergeCommit": {"oid": "sha123"}}},  # pr view for merge sha
                ],
            ),
            patch(
                "sdd_orchestrator.tools.github.asyncio.create_subprocess_exec", return_value=mock_proc
            ),
            patch("sdd_orchestrator.tools.github.asyncio.wait_for", return_value=(b"", b"")),
            patch("sdd_orchestrator.rules.can_auto_merge", return_value=(True, "")),
            patch("sdd_orchestrator.tools.rollback.start_post_merge_monitor") as mock_monitor,
            patch("sdd_orchestrator.config.SENTRY_AUTH_TOKEN", "fake-token"),
        ):
            result = await do_merge_pr(50)

        assert not result.get("isError", False)
        mock_monitor.assert_called_once_with(50, "sha123")
