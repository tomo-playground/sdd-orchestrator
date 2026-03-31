"""Unit tests for GitHub Issue → SDD Task bridge."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sdd_orchestrator.tools.issues import (
    GH_ISSUE_RE,
    _extract_description,
    _extract_title,
    _get_existing_issue_mappings,
    do_auto_create_task,
    do_scan_issues,
    set_state_store,
)

# ── Helpers ──────────────────────────────────────────────────


def _make_issue(number: int, title: str = "Bug", labels: list[str] | None = None) -> dict:
    label_objs = [{"name": l} for l in (labels or ["bug"])]
    return {
        "number": number,
        "title": title,
        "body": "Some description",
        "labels": label_objs,
        "createdAt": "2026-03-30T00:00:00Z",
    }


class TestExtractTitle:
    def test_strips_sentry_prefix(self):
        issue = {"title": "[Sentry/backend] ZeroDivisionError"}
        assert _extract_title(issue) == "ZeroDivisionError"

    def test_plain_title(self):
        issue = {"title": "Fix login bug"}
        assert _extract_title(issue) == "Fix login bug"


class TestExtractDescription:
    def test_truncates_long_body(self):
        issue = {"body": "x" * 5000}
        result = _extract_description(issue)
        assert len(result) < 5000
        assert result.endswith("[truncated]")

    def test_empty_body(self):
        issue = {"body": None}
        assert _extract_description(issue) == ""


class TestGetExistingIssueMappings:
    def test_parses_gh_issue_from_spec(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        current.mkdir()
        done.mkdir()

        task_dir = current / "SP-001_fix-bug"
        task_dir.mkdir()
        (task_dir / "spec.md").write_text("- **gh_issue**: #42\n")

        result = _get_existing_issue_mappings(current, done)
        assert 42 in result

    def test_empty_dirs(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        current.mkdir()
        done.mkdir()

        result = _get_existing_issue_mappings(current, done)
        assert result == set()


class TestGhIssueRegex:
    def test_matches_bold(self):
        assert GH_ISSUE_RE.search("**gh_issue**: #42").group(1) == "42"

    def test_matches_plain(self):
        assert GH_ISSUE_RE.search("gh_issue: 42").group(1) == "42"


class TestDoScanIssues:
    @pytest.mark.asyncio
    async def test_skips_linked_issues(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        current.mkdir()
        done.mkdir()

        task_dir = current / "SP-001_fix-bug"
        task_dir.mkdir()
        (task_dir / "spec.md").write_text("- **gh_issue**: #10\n")

        issues = [_make_issue(10), _make_issue(11)]
        with patch(
            "sdd_orchestrator.tools.issues._fetch_labeled_issues",
            new_callable=AsyncMock,
            return_value=(issues, None),
        ):
            result = await do_scan_issues(current, done)

        data = json.loads(result["content"][0]["text"])
        assert data["already_linked"] == 1
        unlinked_nums = [i["number"] for i in data["unlinked_issues"]]
        assert 10 not in unlinked_nums
        assert 11 in unlinked_nums

    @pytest.mark.asyncio
    async def test_fetch_error_reported(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        current.mkdir()
        done.mkdir()

        with patch(
            "sdd_orchestrator.tools.issues._fetch_labeled_issues",
            new_callable=AsyncMock,
            return_value=([], "timeout"),
        ):
            result = await do_scan_issues(current, done)

        data = json.loads(result["content"][0]["text"])
        assert "fetch_errors" in data


class TestDoAutoCreateTask:
    @pytest.mark.asyncio
    async def test_creates_spec_with_metadata(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        backlog = tmp_path / "backlog.md"
        current.mkdir()
        done.mkdir()
        backlog.write_text("")

        store = MagicMock()
        set_state_store(store)

        issue = _make_issue(42, title="Fix login redirect")

        with patch(
            "sdd_orchestrator.tools.issues.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_auto_create_task(issue, current, done, backlog)

        data = json.loads(result["content"][0]["text"])
        assert data["issue_number"] == 42
        assert data["priority"] == "P2"

        spec_files = list(current.glob("SP-*_*/spec.md"))
        assert len(spec_files) == 1
        content = spec_files[0].read_text()
        assert "gh_issue" in content
        assert "#42" in content
        assert "scope**: tbd" in content
        store.set_task_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_already_linked(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        backlog = tmp_path / "backlog.md"
        current.mkdir()
        done.mkdir()
        backlog.write_text("")

        task_dir = current / "SP-001_fix"
        task_dir.mkdir()
        (task_dir / "spec.md").write_text("- **gh_issue**: #42\n")

        store = MagicMock()
        set_state_store(store)

        issue = _make_issue(42)
        result = await do_auto_create_task(issue, current, done, backlog)

        data = json.loads(result["content"][0]["text"])
        assert data["skipped"] is True

    @pytest.mark.asyncio
    async def test_rollback_on_git_failure(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        backlog = tmp_path / "backlog.md"
        current.mkdir()
        done.mkdir()
        backlog.write_text("")

        store = MagicMock()
        set_state_store(store)

        issue = _make_issue(99, title="Crash on start")

        with (
            patch(
                "sdd_orchestrator.tools.issues.git_commit_files",
                new_callable=AsyncMock,
                return_value="commit failed",
            ),
            patch(
                "sdd_orchestrator.tools.issues.git_reset_files",
                new_callable=AsyncMock,
            ) as mock_reset,
        ):
            result = await do_auto_create_task(issue, current, done, backlog)

        assert result.get("isError") is True
        assert "Git 커밋 실패" in result["content"][0]["text"]
        mock_reset.assert_called_once()
        store.set_task_status.assert_not_called()
        # Task directory should be cleaned up
        assert list(current.glob("SP-*_*/spec.md")) == []

    @pytest.mark.asyncio
    async def test_sentry_label_gets_p1(self, tmp_path):
        current = tmp_path / "current"
        done = tmp_path / "done"
        backlog = tmp_path / "backlog.md"
        current.mkdir()
        done.mkdir()
        backlog.write_text("")

        store = MagicMock()
        set_state_store(store)

        issue = _make_issue(50, title="Sentry error", labels=["sentry"])

        with patch(
            "sdd_orchestrator.tools.issues.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_auto_create_task(issue, current, done, backlog)

        data = json.loads(result["content"][0]["text"])
        assert data["priority"] == "P1"

    @pytest.mark.asyncio
    async def test_rollback_undoes_local_commit_on_push_failure(self, tmp_path):
        """Push failure (commit exists locally) should call git_undo_last_commit."""
        current = tmp_path / "current"
        done = tmp_path / "done"
        backlog = tmp_path / "backlog.md"
        current.mkdir()
        done.mkdir()
        backlog.write_text("")

        store = MagicMock()
        set_state_store(store)

        issue = _make_issue(77, title="Push fail test")

        with (
            patch(
                "sdd_orchestrator.tools.issues.git_commit_files",
                new_callable=AsyncMock,
                return_value="git push retry failed: remote rejected",
            ),
            patch(
                "sdd_orchestrator.tools.issues.git_reset_files",
                new_callable=AsyncMock,
            ) as mock_reset,
            patch(
                "sdd_orchestrator.tools.task_utils.git_undo_last_commit",
                new_callable=AsyncMock,
            ) as mock_undo,
        ):
            result = await do_auto_create_task(issue, current, done, backlog)

        assert result.get("isError") is True
        mock_undo.assert_called_once()
        mock_reset.assert_not_called()
        store.set_task_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_state_store_returns_error(self):
        set_state_store(None)
        issue = _make_issue(1)
        result = await do_auto_create_task(issue)
        assert result.get("isError") is True
