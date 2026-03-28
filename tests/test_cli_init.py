"""Tests for sdd init CLI command."""

from __future__ import annotations

from pathlib import Path

from sdd_orchestrator.cli.init import run_init


def test_init_creates_files(tmp_path: Path, monkeypatch):
    """sdd init creates config and task directories."""
    monkeypatch.chdir(tmp_path)
    result = run_init()
    assert result == 0
    assert (tmp_path / "sdd.config.yaml").exists()
    assert (tmp_path / ".claude/tasks/backlog.md").exists()
    assert (tmp_path / ".claude/tasks/current").is_dir()
    assert (tmp_path / ".claude/tasks/done").is_dir()
    assert (tmp_path / ".claude/agents").is_dir()
    assert (tmp_path / ".claude/skills").is_dir()
    assert (tmp_path / ".github/workflows/sdd-sync.yml").exists()
    assert (tmp_path / ".github/workflows/health-check.yml").exists()


def test_init_skips_existing(tmp_path: Path, monkeypatch):
    """sdd init skips files that already exist."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sdd.config.yaml").write_text("custom: true")
    result = run_init()
    assert result == 0
    assert (tmp_path / "sdd.config.yaml").read_text() == "custom: true"


def test_init_force_overwrites(tmp_path: Path, monkeypatch):
    """sdd init --force overwrites existing files."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sdd.config.yaml").write_text("custom: true")
    result = run_init(force=True)
    assert result == 0
    content = (tmp_path / "sdd.config.yaml").read_text()
    assert "your-org" in content
