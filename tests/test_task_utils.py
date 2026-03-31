"""Unit tests for task_utils shared helpers."""

from __future__ import annotations

from pathlib import Path

from sdd_orchestrator.tools.task_utils import (
    generate_slug,
    next_sp_number,
)


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
