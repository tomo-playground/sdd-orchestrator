"""Unit tests for backlog parser."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from sdd_orchestrator.state import StateStore
from sdd_orchestrator.tools.backlog import parse_backlog, set_state_store


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    s = StateStore(db_path=tmp_path / "test_state.db")
    set_state_store(s)
    yield s
    set_state_store(None)


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


def test_parse_backlog_basic(backlog_file: Path, tmp_path: Path):
    """Test basic parsing of tasks with priorities."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    assert len(tasks) == 5

    ids = [t.id for t in tasks]
    assert "SP-066" in ids
    assert "SP-067" in ids
    assert "SP-058" in ids
    assert "SP-020" in ids
    assert "SP-072" in ids


def test_parse_backlog_priorities(backlog_file: Path, tmp_path: Path):
    """Test that priorities are correctly assigned from section headers."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-066"].priority == "P0"
    assert by_id["SP-067"].priority == "P0"
    assert by_id["SP-058"].priority == "P1"
    assert by_id["SP-020"].priority == "P1"
    assert by_id["SP-072"].priority == "P2"


def test_parse_backlog_depends(backlog_file: Path, tmp_path: Path):
    """Test depends_on extraction."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-067"].depends_on == ["SP-066"]
    assert by_id["SP-058"].depends_on == ["SP-056"]
    assert by_id["SP-066"].depends_on == []


def test_parse_backlog_scope(backlog_file: Path, tmp_path: Path):
    """Test scope metadata extraction."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-066"].scope == "infra"
    assert by_id["SP-072"].scope == "backend"
    assert by_id["SP-020"].scope == ""


def test_parse_backlog_approved_flag(backlog_file: Path, tmp_path: Path):
    """Test **approved** flag detection."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    by_id = {t.id: t for t in tasks}

    assert by_id["SP-058"].backlog_approved is True
    assert by_id["SP-066"].backlog_approved is False


def test_parse_backlog_skips_done_section(backlog_file: Path, tmp_path: Path):
    """Test that completed tasks (완료 section) are skipped."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    ids = [t.id for t in tasks]
    assert "SP-001" not in ids
    assert "SP-002" not in ids
    assert "SP-003" not in ids


def test_parse_backlog_empty_file(tmp_path: Path):
    """Test parsing an empty backlog file."""
    f = tmp_path / "backlog.md"
    f.write_text("# Backlog\n\nNothing here.\n", encoding="utf-8")
    tasks = parse_backlog(f, current_dir=tmp_path / "empty")
    assert tasks == []


def test_parse_backlog_missing_file(tmp_path: Path):
    """Test parsing a nonexistent file returns empty list."""
    f = tmp_path / "nonexistent.md"
    tasks = parse_backlog(f, current_dir=tmp_path / "empty")
    assert tasks == []


def test_parse_backlog_description_cleaning(backlog_file: Path, tmp_path: Path):
    """Test that descriptions are cleaned of metadata and links."""
    tasks = parse_backlog(backlog_file, current_dir=tmp_path / "empty")
    by_id = {t.id: t for t in tasks}

    assert "scope:" not in by_id["SP-066"].description
    assert "[명세]" not in by_id["SP-020"].description


def test_parse_backlog_enrichment_with_spec(tmp_path: Path, store: StateStore):
    """Test enrichment from state.db for tasks in current/ directory."""
    # Create backlog
    backlog = tmp_path / "backlog.md"
    backlog.write_text("## P0\n\n- [ ] SP-099 — Test task\n", encoding="utf-8")

    # Create task spec directory
    task_dir = tmp_path / "current" / "SP-099_test-task"
    task_dir.mkdir(parents=True)
    (task_dir / "spec.md").write_text("# SP-099: Test\n\n## What\nTest\n", encoding="utf-8")
    (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")

    # Set status in DB
    store.set_task_status("SP-099", "approved")

    tasks = parse_backlog(backlog, current_dir=tmp_path / "current")
    assert len(tasks) == 1
    assert tasks[0].spec_status == "approved"
    assert tasks[0].has_design is True


def test_blockquote_status_enrichment(tmp_path: Path, store: StateStore):
    """Status is read from state.db, not spec.md."""
    backlog = tmp_path / "backlog.md"
    backlog.write_text("## P0\n\n- [ ] SP-087 — Slack workflow\n", encoding="utf-8")

    task_dir = tmp_path / "current" / "SP-087_slack-workflow"
    task_dir.mkdir(parents=True)
    (task_dir / "spec.md").write_text("# SP-087\n\n## DoD\n", encoding="utf-8")
    (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")

    store.set_task_status("SP-087", "approved")

    tasks = parse_backlog(backlog, current_dir=tmp_path / "current")
    assert tasks[0].spec_status == "approved"


def test_blockquote_status_discover(tmp_path: Path, store: StateStore):
    """Discovered tasks read status from state.db."""
    backlog = tmp_path / "backlog.md"
    backlog.write_text("# Backlog\n\n## P1\n\n", encoding="utf-8")

    task_dir = tmp_path / "current" / "SP-086_slack-templates"
    task_dir.mkdir(parents=True)
    (task_dir / "spec.md").write_text(
        "# SP-086\n\npriority: P0\nscope: infra\n",
        encoding="utf-8",
    )

    store.set_task_status("SP-086", "approved")

    tasks = parse_backlog(backlog, current_dir=tmp_path / "current")
    assert tasks[0].spec_status == "approved"
    assert tasks[0].priority == "P0"
    assert tasks[0].scope == "infra"


def test_discover_current_tasks_not_in_backlog(tmp_path: Path, store: StateStore):
    """Tasks in current/ but NOT in backlog.md are discovered."""
    # Empty backlog
    backlog = tmp_path / "backlog.md"
    backlog.write_text("# Backlog\n\n## P1\n\n", encoding="utf-8")

    # Task only in current/
    task_dir = tmp_path / "current" / "SP-084_comfyui-cleanup"
    task_dir.mkdir(parents=True)
    (task_dir / "spec.md").write_text(
        "# SP-084: Cleanup\n\npriority: P1\nscope: backend\n",
        encoding="utf-8",
    )
    (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")

    store.set_task_status("SP-084", "approved")

    tasks = parse_backlog(backlog, current_dir=tmp_path / "current")
    assert len(tasks) == 1
    assert tasks[0].id == "SP-084"
    assert tasks[0].spec_status == "approved"
    assert tasks[0].has_design is True


def test_discover_does_not_duplicate_backlog_tasks(tmp_path: Path, store: StateStore):
    """Tasks in both backlog.md AND current/ are not duplicated."""
    backlog = tmp_path / "backlog.md"
    backlog.write_text(
        "# Backlog\n\n## P1\n\n- [ ] SP-099 — Test task\n",
        encoding="utf-8",
    )

    task_dir = tmp_path / "current" / "SP-099_test-task"
    task_dir.mkdir(parents=True)
    (task_dir / "spec.md").write_text("# SP-099\n", encoding="utf-8")

    store.set_task_status("SP-099", "approved")

    tasks = parse_backlog(backlog, current_dir=tmp_path / "current")
    assert len(tasks) == 1
    assert tasks[0].id == "SP-099"
    assert tasks[0].spec_status == "approved"
