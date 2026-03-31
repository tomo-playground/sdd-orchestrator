"""Unit tests for tasks MCP tools (read_task, approve_design, create_task)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sdd_orchestrator.state import StateStore
from sdd_orchestrator.tools.tasks import (
    do_approve_design,
    do_create_task,
    do_read_task,
    set_state_store,
)


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    s = StateStore(db_path=tmp_path / "test_state.db")
    set_state_store(s)
    yield s
    set_state_store(None)


@pytest.fixture()
def task_dirs(tmp_path: Path, store: StateStore):
    """Create current/ and done/ directories with a sample task."""
    current = tmp_path / "current"
    current.mkdir()
    done = tmp_path / "done"
    done.mkdir()

    task_dir = current / "SP-086_slack-templates"
    task_dir.mkdir()
    (task_dir / "spec.md").write_text(
        "# SP-086: Slack Templates\n\n## DoD\n\n1. Done\n",
        encoding="utf-8",
    )
    (task_dir / "design.md").write_text(
        "# Design\n\n## DoD 1\n\nImplementation details.\n",
        encoding="utf-8",
    )
    # Set status in DB
    store.set_task_status("SP-086", "approved")
    return current, done


class TestReadTask:
    async def test_read_existing_task(self, task_dirs):
        current, done = task_dirs
        result = await do_read_task("SP-086", current, done)
        assert "isError" not in result
        data = json.loads(result["content"][0]["text"])
        assert data["task_id"] == "SP-086"
        assert data["status"] == "approved"
        assert data["has_design"] is True
        assert "Slack Templates" in data["spec"]
        assert "Implementation details" in data["design"]

    async def test_read_task_not_found(self, task_dirs):
        current, done = task_dirs
        result = await do_read_task("SP-999", current, done)
        assert result["isError"] is True
        assert "not found" in result["content"][0]["text"]

    async def test_read_task_invalid_id_format(self, task_dirs):
        current, done = task_dirs
        result = await do_read_task("SP-9999", current, done)
        assert result["isError"] is True
        assert "형식" in result["content"][0]["text"]

    async def test_read_task_ambiguous(self, task_dirs):
        current, done = task_dirs
        # Create a second directory with the same SP number
        dup = current / "SP-086_duplicate"
        dup.mkdir()
        (dup / "spec.md").write_text("# SP-086 dup\n", encoding="utf-8")
        result = await do_read_task("SP-086", current, done)
        assert result["isError"] is True
        assert "중복" in result["content"][0]["text"]

    async def test_read_task_no_design(self, task_dirs):
        current, done = task_dirs
        # Remove design.md
        (current / "SP-086_slack-templates" / "design.md").unlink()
        result = await do_read_task("SP-086", current, done)
        data = json.loads(result["content"][0]["text"])
        assert data["has_design"] is False
        assert data["design"] is None

    async def test_read_task_truncation(self, task_dirs):
        current, done = task_dirs
        # Write a very long spec
        long_content = "# SP-086\n\n" + "x" * 10000
        (current / "SP-086_slack-templates" / "spec.md").write_text(long_content, encoding="utf-8")
        result = await do_read_task("SP-086", current, done)
        data = json.loads(result["content"][0]["text"])
        assert len(data["spec"]) < len(long_content)
        assert "[TRUNCATED" in data["spec"]

    async def test_read_done_task(self, task_dirs, store):
        current, done = task_dirs
        # Move task to done/
        task_dir = done / "SP-050_old-task"
        task_dir.mkdir()
        (task_dir / "spec.md").write_text("# SP-050\n", encoding="utf-8")
        store.set_task_status("SP-050", "done")
        result = await do_read_task("SP-050", current, done)
        data = json.loads(result["content"][0]["text"])
        assert data["task_id"] == "SP-050"
        assert data["status"] == "done"

    async def test_read_legacy_md_file(self, task_dirs, store):
        current, done = task_dirs
        (done / "SP-030_legacy-task.md").write_text(
            "# SP-030\n\nLegacy content.\n",
            encoding="utf-8",
        )
        store.set_task_status("SP-030", "done")
        result = await do_read_task("SP-030", current, done)
        data = json.loads(result["content"][0]["text"])
        assert data["task_id"] == "SP-030"
        assert data["status"] == "done"
        assert data["has_design"] is False
        assert "Legacy content" in data["spec"]


class TestApproveDesign:
    async def test_approve_success(self, task_dirs, store):
        current, _ = task_dirs
        # Set status to design (approvable)
        store.set_task_status("SP-086", "design")
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_approve_design("SP-086", current)

        assert "isError" not in result
        assert "승인 완료" in result["content"][0]["text"]
        assert store.get_task_status("SP-086") == "approved"

    async def test_approve_no_design(self, task_dirs):
        current, _ = task_dirs
        (current / "SP-086_slack-templates" / "design.md").unlink()
        result = await do_approve_design("SP-086", current)
        assert result["isError"] is True
        assert "설계 파일" in result["content"][0]["text"]

    async def test_approve_already_approved(self, task_dirs):
        current, _ = task_dirs
        result = await do_approve_design("SP-086", current)
        assert result["isError"] is True
        assert "이미 승인" in result["content"][0]["text"]

    async def test_approve_task_not_found(self, task_dirs):
        current, _ = task_dirs
        result = await do_approve_design("SP-999", current)
        assert result["isError"] is True
        assert "not found" in result["content"][0]["text"]

    async def test_approve_pending_status(self, task_dirs, store):
        current, _ = task_dirs
        store.set_task_status("SP-086", "pending")
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_approve_design("SP-086", current)
        assert "isError" not in result
        assert "승인 완료" in result["content"][0]["text"]

    async def test_approve_git_failure(self, task_dirs, store):
        current, _ = task_dirs
        store.set_task_status("SP-086", "design")
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value="git push failed",
        ):
            result = await do_approve_design("SP-086", current)
        assert result["isError"] is True
        assert "Git" in result["content"][0]["text"]
        # DB status must be rolled back to original
        assert store.get_task_status("SP-086") == "design"


class TestCreateTask:
    async def test_create_basic(self, task_dirs, tmp_path, store):
        current, done = task_dirs
        backlog = tmp_path / "backlog.md"
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_create_task("Slack Enhancement", "", current, done, backlog)

        assert "isError" not in result
        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "pending"
        assert "SP-" in data["task_id"]

        # Verify directory was created
        task_dir = current / data["directory"]
        assert task_dir.exists()
        assert (task_dir / "spec.md").exists()
        # Verify status in DB
        assert store.get_task_status(data["task_id"]) == "pending"

    async def test_auto_increment_sp_number(self, task_dirs, tmp_path):
        current, done = task_dirs
        backlog = tmp_path / "backlog.md"
        # SP-086 already exists in current/
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_create_task("New Task", "", current, done, backlog)

        data = json.loads(result["content"][0]["text"])
        # Should be SP-087 (86 + 1)
        assert data["task_id"] == "SP-087"

    async def test_korean_only_title_slug(self, task_dirs, tmp_path):
        current, done = task_dirs
        backlog = tmp_path / "backlog.md"
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_create_task("슬랙 메시지 개선", "", current, done, backlog)

        data = json.loads(result["content"][0]["text"])
        assert "task" in data["directory"]  # fallback slug

    async def test_empty_title_error(self, task_dirs):
        current, done = task_dirs
        result = await do_create_task("", "", current, done)
        assert result["isError"] is True
        assert "비어" in result["content"][0]["text"]

    async def test_create_collision_retries(self, task_dirs, tmp_path):
        current, done = task_dirs
        backlog = tmp_path / "backlog.md"
        # Return 87 twice to force FileExistsError on first attempt
        call_count = 0

        def mock_sp(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            return 87 if call_count == 1 else 88

        (current / "SP-087_slack-enhancement").mkdir()  # pre-existing to cause collision
        with (
            patch("sdd_orchestrator.tools.tasks.next_sp_number", side_effect=mock_sp),
            patch(
                "sdd_orchestrator.tools.tasks.git_commit_files",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await do_create_task("Slack Enhancement", "", current, done, backlog)
        assert "isError" not in result
        data = json.loads(result["content"][0]["text"])
        assert data["task_id"] == "SP-088"
        assert call_count == 2  # retried once

    async def test_with_description(self, task_dirs, tmp_path):
        current, done = task_dirs
        backlog = tmp_path / "backlog.md"
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await do_create_task(
                "Fix Bug", "Critical issue in production", current, done, backlog
            )

        data = json.loads(result["content"][0]["text"])
        spec = (current / data["directory"] / "spec.md").read_text(encoding="utf-8")
        assert "Critical issue" in spec

    async def test_create_git_failure_rollback(self, task_dirs, tmp_path, store):
        current, done = task_dirs
        backlog = tmp_path / "backlog.md"
        with patch(
            "sdd_orchestrator.tools.tasks.git_commit_files",
            new_callable=AsyncMock,
            return_value="git push failed",
        ):
            result = await do_create_task("New Task", "", current, done, backlog)
        assert result["isError"] is True
        assert "Git" in result["content"][0]["text"]
        # task_dir must be rolled back (removed) on git failure
        assert not any(current.glob("SP-087_*"))
        # DB row must also be cleaned up (no phantom task)
        row = store.conn.execute("SELECT 1 FROM task_status WHERE task_id = 'SP-087'").fetchone()
        assert row is None
