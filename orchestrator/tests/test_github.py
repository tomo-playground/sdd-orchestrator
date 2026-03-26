"""Unit tests for GitHub CLI wrappers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from orchestrator.tools.github import (
    _aggregate_check_status,
    _run_gh_command,
    detect_stuck_runs,
    summarize_prs,
)


class TestSummarizePrs:
    def test_basic_pr_summary(self):
        prs = [
            {
                "number": 42,
                "title": "feat: add X",
                "headRefName": "feat/SP-066-orchestrator",
                "state": "OPEN",
                "reviewDecision": "APPROVED",
                "statusCheckRollup": [{"conclusion": "SUCCESS"}],
                "labels": [{"name": "feat"}],
            }
        ]
        result = summarize_prs(prs)
        assert len(result) == 1
        assert result[0]["number"] == 42
        assert result[0]["task_id"] == "SP-066"
        assert result[0]["review"] == "APPROVED"
        assert result[0]["ci_status"] == "success"
        assert result[0]["mergeable"] is True
        assert result[0]["labels"] == ["feat"]

    def test_no_sp_match(self):
        prs = [
            {
                "number": 1,
                "title": "chore: update deps",
                "headRefName": "chore/deps",
                "state": "OPEN",
                "reviewDecision": None,
                "statusCheckRollup": [],
                "labels": [],
            }
        ]
        result = summarize_prs(prs)
        assert result[0]["task_id"] is None

    def test_empty_prs(self):
        assert summarize_prs([]) == []

    def test_multiple_checks(self):
        prs = [
            {
                "number": 5,
                "title": "fix",
                "headRefName": "fix/SP-010-bug",
                "state": "OPEN",
                "reviewDecision": "CHANGES_REQUESTED",
                "statusCheckRollup": [
                    {"conclusion": "SUCCESS"},
                    {"conclusion": "FAILURE"},
                ],
                "labels": [],
            }
        ]
        result = summarize_prs(prs)
        assert result[0]["ci_status"] == "failure"
        assert result[0]["task_id"] == "SP-010"


class TestAggregateCheckStatus:
    def test_empty_checks(self):
        assert _aggregate_check_status([]) == "none"

    def test_all_success(self):
        checks = [{"conclusion": "SUCCESS"}, {"conclusion": "SUCCESS"}]
        assert _aggregate_check_status(checks) == "success"

    def test_any_failure(self):
        checks = [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]
        assert _aggregate_check_status(checks) == "failure"

    def test_pending(self):
        checks = [{"conclusion": "SUCCESS"}, {"status": "PENDING"}]
        assert _aggregate_check_status(checks) == "pending"

    def test_in_progress(self):
        checks = [{"conclusion": "SUCCESS"}, {"status": "IN_PROGRESS"}]
        assert _aggregate_check_status(checks) == "pending"

    def test_queued(self):
        checks = [{"conclusion": "SUCCESS"}, {"status": "QUEUED"}]
        assert _aggregate_check_status(checks) == "pending"

    def test_empty_conclusion_pending(self):
        checks = [{"conclusion": "SUCCESS"}, {"conclusion": ""}]
        assert _aggregate_check_status(checks) == "pending"


class TestDetectStuckRuns:
    def test_no_stuck(self):
        now = datetime.now(UTC)
        runs = [
            {"status": "in_progress", "createdAt": (now - timedelta(minutes=10)).isoformat()},
            {"status": "completed", "conclusion": "success", "createdAt": now.isoformat()},
        ]
        assert detect_stuck_runs(runs) == []

    def test_stuck_detected(self):
        old_time = datetime.now(UTC) - timedelta(minutes=45)
        runs = [
            {
                "status": "in_progress",
                "createdAt": old_time.isoformat(),
                "workflowName": "ci",
                "databaseId": 123,
            }
        ]
        stuck = detect_stuck_runs(runs)
        assert len(stuck) == 1
        assert stuck[0]["databaseId"] == 123
        assert stuck[0]["elapsed_minutes"] >= 45

    def test_completed_not_stuck(self):
        old_time = datetime.now(UTC) - timedelta(hours=2)
        runs = [{"status": "completed", "conclusion": "success", "createdAt": old_time.isoformat()}]
        assert detect_stuck_runs(runs) == []

    def test_invalid_date(self):
        runs = [{"status": "in_progress", "createdAt": "not-a-date"}]
        assert detect_stuck_runs(runs) == []


class TestRunGhCommand:
    @pytest.mark.asyncio
    async def test_successful_command(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'[{"number": 1}]', b"")
        mock_proc.returncode = 0

        with patch("orchestrator.tools.github.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc
            result = await _run_gh_command("pr", "list", "--json", "number")

        assert "data" in result
        assert result["data"] == [{"number": 1}]

    @pytest.mark.asyncio
    async def test_command_failure(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"not authenticated")
        mock_proc.returncode = 1

        with patch("orchestrator.tools.github.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc
            result = await _run_gh_command("pr", "list")

        assert "error" in result
        assert "not authenticated" in result["error"]

    @pytest.mark.asyncio
    async def test_timeout(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = TimeoutError()

        with patch("orchestrator.tools.github.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc
            result = await _run_gh_command("pr", "list")

        assert "error" in result
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_gh_not_found(self):
        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError,
        ):
            result = await _run_gh_command("pr", "list")

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestSummarizePrsMergeable:
    def test_mergeable_true(self):
        prs = [
            {
                "number": 1,
                "title": "feat",
                "headRefName": "feat/SP-001",
                "reviewDecision": "APPROVED",
                "statusCheckRollup": [{"conclusion": "SUCCESS"}],
                "labels": [],
            }
        ]
        result = summarize_prs(prs)
        assert result[0]["mergeable"] is True

    def test_mergeable_false_ci_fail(self):
        prs = [
            {
                "number": 1,
                "title": "feat",
                "headRefName": "feat/SP-001",
                "reviewDecision": "APPROVED",
                "statusCheckRollup": [{"conclusion": "FAILURE"}],
                "labels": [],
            }
        ]
        result = summarize_prs(prs)
        assert result[0]["mergeable"] is False

    def test_mergeable_false_no_review(self):
        prs = [
            {
                "number": 1,
                "title": "feat",
                "headRefName": "feat/SP-001",
                "reviewDecision": None,
                "statusCheckRollup": [{"conclusion": "SUCCESS"}],
                "labels": [],
            }
        ]
        result = summarize_prs(prs)
        assert result[0]["mergeable"] is False


def _mock_pr_view_approved():
    """Helper: mock gh pr view returning an approved PR with passing CI."""
    return {
        "data": {
            "number": 42,
            "title": "feat: test",
            "headRefName": "feat/SP-099",
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"conclusion": "SUCCESS"}],
            "labels": [],
        }
    }


class TestMergePr:
    @pytest.mark.asyncio
    async def test_merge_success(self):
        from orchestrator.tools.github import do_merge_pr

        # Mock: first call = pr view (JSON), second call = pr merge (text),
        # third call = pr view for merge SHA (JSON)
        view_proc = AsyncMock()
        view_proc.communicate.return_value = (
            json.dumps(_mock_pr_view_approved()["data"]).encode(),
            b"",
        )
        view_proc.returncode = 0

        merge_proc = AsyncMock()
        merge_proc.communicate.return_value = (b"Merged", b"")
        merge_proc.returncode = 0

        sha_proc = AsyncMock()
        sha_proc.communicate.return_value = (
            json.dumps({"mergeCommit": {"oid": "abc123"}}).encode(),
            b"",
        )
        sha_proc.returncode = 0

        with (
            patch(
                "orchestrator.tools.github.asyncio.create_subprocess_exec",
                side_effect=[view_proc, merge_proc, sha_proc],
            ),
            patch("orchestrator.tools.rollback.start_post_merge_monitor"),
        ):
            result = await do_merge_pr(42)

        assert "isError" not in result
        assert "42" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_merge_blocked_by_rules(self):
        from orchestrator.tools.github import do_merge_pr

        # PR with failing CI
        view_proc = AsyncMock()
        pr_data = _mock_pr_view_approved()["data"].copy()
        pr_data["statusCheckRollup"] = [{"conclusion": "FAILURE"}]
        view_proc.communicate.return_value = (json.dumps(pr_data).encode(), b"")
        view_proc.returncode = 0

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=view_proc,
        ):
            result = await do_merge_pr(42)

        assert result.get("isError") is True
        assert "CI" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_merge_gh_failure(self):
        from orchestrator.tools.github import do_merge_pr

        view_proc = AsyncMock()
        view_proc.communicate.return_value = (
            json.dumps(_mock_pr_view_approved()["data"]).encode(),
            b"",
        )
        view_proc.returncode = 0

        merge_proc = AsyncMock()
        merge_proc.communicate.return_value = (b"", b"merge conflict")
        merge_proc.returncode = 1

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            side_effect=[view_proc, merge_proc],
        ):
            result = await do_merge_pr(42)

        assert result.get("isError") is True
        assert "merge conflict" in result["content"][0]["text"]


class TestTriggerSddReview:
    @pytest.mark.asyncio
    async def test_trigger_success(self):
        from orchestrator.tools.github import do_trigger_sdd_review

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await do_trigger_sdd_review(42)

        assert "isError" not in result
        assert "42" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_trigger_failure(self):
        from orchestrator.tools.github import do_trigger_sdd_review

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"workflow not found")
        mock_proc.returncode = 1

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await do_trigger_sdd_review(42)

        assert result.get("isError") is True
