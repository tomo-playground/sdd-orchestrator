"""Unit tests for task_utils shared helpers."""

from __future__ import annotations

from pathlib import Path

from sdd_orchestrator.tools.task_utils import (
    generate_slug,
    next_sp_number,
    parse_spec_status,
    update_spec_status,
)


class TestParseSpecStatus:
    def test_frontmatter_format(self):
        content = "---\nstatus: approved\n---\n## What\n"
        assert parse_spec_status(content) == "approved"

    def test_blockquote_format(self):
        content = "# SP-087\n\n> status: approved\n"
        assert parse_spec_status(content) == "approved"

    def test_blockquote_with_pipe_metadata(self):
        content = "# SP-087\n\n> status: approved | approved_at: 2026-03-26\n"
        assert parse_spec_status(content) == "approved"

    def test_no_status_returns_pending(self):
        content = "# SP-087\n\n## What\nSomething\n"
        assert parse_spec_status(content) == "pending"

    def test_running_status(self):
        content = "> status: running | approved_at: 2026-03-26\n"
        assert parse_spec_status(content) == "running"

    def test_design_status_frontmatter(self):
        content = "---\nstatus: design\n---\n"
        assert parse_spec_status(content) == "design"


class TestUpdateSpecStatus:
    def test_replace_existing_blockquote(self):
        content = "# Title\n\n> status: pending\n\n## What\n"
        result = update_spec_status(content, "approved", "approved_at: 2026-03-26")
        assert "> status: approved | approved_at: 2026-03-26" in result
        assert "pending" not in result

    def test_replace_existing_frontmatter(self):
        content = "---\nstatus: pending\n---\n## What\n"
        result = update_spec_status(content, "design")
        assert "> status: design" in result
        assert "pending" not in result

    def test_insert_when_missing(self):
        content = "# SP-087: Title\n\n## What\n"
        result = update_spec_status(content, "pending")
        assert "> status: pending" in result

    def test_with_metadata(self):
        content = "# Title\n\n> status: design\n"
        result = update_spec_status(content, "approved", "approved_at: 2026-03-26")
        assert "> status: approved | approved_at: 2026-03-26" in result


class TestGenerateSlug:
    def test_english_title(self):
        assert generate_slug("Slack Workflow Enhancement") == "slack-workflow-enhancement"

    def test_korean_only_fallback(self):
        assert generate_slug("태스크 만들기") == "task"

    def test_mixed_korean_english(self):
        slug = generate_slug("Slack 메시지 Template")
        assert slug == "slack-template"

    def test_special_characters(self):
        slug = generate_slug("Fix bug #123 (urgent!)")
        assert slug == "fix-bug-123-urgent"

    def test_max_length(self):
        slug = generate_slug("A very long title " * 5, max_len=20)
        assert len(slug) <= 20

    def test_empty_string(self):
        assert generate_slug("") == "task"


class TestNextSpNumber:
    def test_scan_directories(self, tmp_path: Path):
        current = tmp_path / "current"
        current.mkdir()
        (current / "SP-010_task").mkdir()
        (current / "SP-020_task").mkdir()
        done = tmp_path / "done"
        done.mkdir()

        result = next_sp_number(current, done, tmp_path / "backlog.md")
        assert result == 21

    def test_scan_legacy_md_files(self, tmp_path: Path):
        current = tmp_path / "current"
        current.mkdir()
        done = tmp_path / "done"
        done.mkdir()
        (done / "SP-050_old-task.md").write_text("# Done", encoding="utf-8")

        result = next_sp_number(current, done, tmp_path / "backlog.md")
        assert result == 51

    def test_scan_backlog(self, tmp_path: Path):
        current = tmp_path / "current"
        current.mkdir()
        done = tmp_path / "done"
        done.mkdir()
        backlog = tmp_path / "backlog.md"
        backlog.write_text("- [ ] SP-100 — task\n", encoding="utf-8")

        result = next_sp_number(current, done, backlog)
        assert result == 101

    def test_empty_directory(self, tmp_path: Path):
        current = tmp_path / "current"
        current.mkdir()
        done = tmp_path / "done"
        done.mkdir()

        result = next_sp_number(current, done, tmp_path / "backlog.md")
        assert result == 1

    def test_mixed_sources(self, tmp_path: Path):
        current = tmp_path / "current"
        current.mkdir()
        (current / "SP-005_a").mkdir()
        done = tmp_path / "done"
        done.mkdir()
        (done / "SP-088_b").mkdir()
        backlog = tmp_path / "backlog.md"
        backlog.write_text("- [ ] SP-070 — task\n", encoding="utf-8")

        result = next_sp_number(current, done, backlog)
        assert result == 89
