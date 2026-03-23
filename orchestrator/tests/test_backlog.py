"""Unit tests for backlog parser."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from orchestrator.tools.backlog import parse_backlog

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def backlog_file(tmp_path: Path) -> Path:
    """Create a sample backlog.md for testing."""
    content = dedent("""\
        # Backlog

        > 실행 가능한 태스크 큐.

        ---

        ## 완료

        - [x] ~~SP-001~~ | ~~SP-002~~ | ~~SP-003~~

        ## P0 (진행 중)

        - [ ] SP-066 — SDD 오케스트레이터 Phase 1: 뼈대 | scope: infra
        - [ ] SP-067 — SDD 오케스트레이터 Phase 2: 자동 실행 | scope: infra | depends: SP-066

        ## P1 (최우선)

        - [ ] SP-058 — Structure 재설계 C: Intake 노드 | **approved** | depends: ~~SP-056~~ ✅
        - [ ] SP-020 — Enum ID 정규화 | [명세](../../docs/FEATURES/ENUM.md)

        ## P2 (기능 확장)

        - [ ] SP-072 — Narrator 씬 지능형 no_humans 판단 | scope: backend
    """)
    f = tmp_path / "backlog.md"
    f.write_text(content, encoding="utf-8")
    return f


def test_parse_backlog_basic(backlog_file: Path):
    """Test basic parsing of tasks with priorities."""
    tasks = parse_backlog(backlog_file)
    assert len(tasks) == 5

    ids = [t.id for t in tasks]
    assert "SP-066" in ids
    assert "SP-067" in ids
    assert "SP-058" in ids
    assert "SP-020" in ids
    assert "SP-072" in ids


def test_parse_backlog_priorities(backlog_file: Path):
    """Test that priorities are correctly assigned from section headers."""
    tasks = parse_backlog(backlog_file)
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-066"].priority == "P0"
    assert by_id["SP-067"].priority == "P0"
    assert by_id["SP-058"].priority == "P1"
    assert by_id["SP-020"].priority == "P1"
    assert by_id["SP-072"].priority == "P2"


def test_parse_backlog_depends(backlog_file: Path):
    """Test depends_on extraction."""
    tasks = parse_backlog(backlog_file)
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-067"].depends_on == ["SP-066"]
    assert by_id["SP-058"].depends_on == ["SP-056"]
    assert by_id["SP-066"].depends_on == []


def test_parse_backlog_scope(backlog_file: Path):
    """Test scope metadata extraction."""
    tasks = parse_backlog(backlog_file)
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-066"].scope == "infra"
    assert by_id["SP-072"].scope == "backend"
    assert by_id["SP-020"].scope == ""


def test_parse_backlog_approved_flag(backlog_file: Path):
    """Test **approved** flag detection."""
    tasks = parse_backlog(backlog_file)
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-058"].backlog_approved is True
    assert by_id["SP-066"].backlog_approved is False


def test_parse_backlog_skips_done_section(backlog_file: Path):
    """Test that completed tasks (완료 section) are skipped."""
    tasks = parse_backlog(backlog_file)
    ids = [t.id for t in tasks]
    assert "SP-001" not in ids
    assert "SP-002" not in ids
    assert "SP-003" not in ids


def test_parse_backlog_empty_file(tmp_path: Path):
    """Test parsing an empty backlog file."""
    f = tmp_path / "backlog.md"
    f.write_text("# Backlog\n\nNothing here.\n", encoding="utf-8")
    tasks = parse_backlog(f)
    assert tasks == []


def test_parse_backlog_missing_file(tmp_path: Path):
    """Test parsing a nonexistent file returns empty list."""
    f = tmp_path / "nonexistent.md"
    tasks = parse_backlog(f)
    assert tasks == []


def test_parse_backlog_description_cleaning(backlog_file: Path):
    """Test that descriptions are cleaned of metadata and links."""
    tasks = parse_backlog(backlog_file)
    by_id = {t.id: t for t in tasks}

    assert "scope:" not in by_id["SP-066"].description
    assert "[명세]" not in by_id["SP-020"].description


def test_parse_backlog_enrichment_with_spec(tmp_path: Path):
    """Test enrichment from spec.md files in current/ directory."""
    # Create backlog
    backlog = tmp_path / "backlog.md"
    backlog.write_text("## P0\n\n- [ ] SP-099 — Test task\n", encoding="utf-8")

    # Create task spec directory
    task_dir = tmp_path / "current" / "SP-099_test-task"
    task_dir.mkdir(parents=True)
    (task_dir / "spec.md").write_text(
        "---\nstatus: approved\n---\n## What\nTest\n", encoding="utf-8"
    )
    (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")

    # Override paths for test
    import orchestrator.tools.backlog as backlog_mod

    original_current = backlog_mod.TASKS_CURRENT_DIR
    backlog_mod.TASKS_CURRENT_DIR = tmp_path / "current"
    try:
        tasks = parse_backlog(backlog)
        assert len(tasks) == 1
        assert tasks[0].spec_status == "approved"
        assert tasks[0].has_design is True
    finally:
        backlog_mod.TASKS_CURRENT_DIR = original_current
