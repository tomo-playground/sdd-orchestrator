"""Unit tests for StateStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdd_orchestrator.state import StateStore


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    """Create a StateStore with a temporary database."""
    return StateStore(db_path=tmp_path / "test_state.db")


def test_tables_created(store: StateStore):
    """Test that tables are created on initialization."""
    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t["name"] for t in tables]
    assert "cycles" in table_names
    assert "decision_log" in table_names


def test_wal_mode(store: StateStore):
    """Test that WAL journal mode is set."""
    row = store.conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0] == "wal"


def test_start_and_finish_cycle(store: StateStore):
    """Test recording a full cycle lifecycle."""
    cycle_id = store.start_cycle()
    assert cycle_id >= 1

    store.finish_cycle(cycle_id, "success", "All clear")

    row = store.conn.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
    assert row["status"] == "success"
    assert row["summary"] == "All clear"
    assert row["started_at"] is not None
    assert row["finished_at"] is not None


def test_log_decision(store: StateStore):
    """Test logging decisions for a cycle."""
    cycle_id = store.start_cycle()
    store.log_decision(cycle_id, "scan", "SP-066", "Task is approved, ready to run")

    rows = store.conn.execute(
        "SELECT * FROM decision_log WHERE cycle_id = ?", (cycle_id,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["action"] == "scan"
    assert rows[0]["target"] == "SP-066"
    assert rows[0]["reason"] == "Task is approved, ready to run"


def test_get_last_cycle_summary_none(store: StateStore):
    """Test getting summary when no cycles exist."""
    assert store.get_last_cycle_summary() is None


def test_get_last_cycle_summary(store: StateStore):
    """Test getting the most recent cycle summary."""
    c1 = store.start_cycle()
    store.finish_cycle(c1, "success", "First cycle OK")

    c2 = store.start_cycle()
    store.finish_cycle(c2, "success", "Second cycle OK")

    assert store.get_last_cycle_summary() == "Second cycle OK"


def test_get_last_cycle_summary_skips_running(store: StateStore):
    """Test that running cycles are excluded from last summary."""
    c1 = store.start_cycle()
    store.finish_cycle(c1, "success", "Completed cycle")

    store.start_cycle()  # Still running

    assert store.get_last_cycle_summary() == "Completed cycle"


def test_get_cycle_count(store: StateStore):
    """Test counting total cycles."""
    assert store.get_cycle_count() == 0

    store.start_cycle()
    assert store.get_cycle_count() == 1

    store.start_cycle()
    assert store.get_cycle_count() == 2


def test_persistence_across_instances(tmp_path: Path):
    """Test that data persists when creating a new StateStore instance."""
    db_path = tmp_path / "persist.db"

    store1 = StateStore(db_path=db_path)
    c1 = store1.start_cycle()
    store1.finish_cycle(c1, "success", "Persisted data")
    store1.close()

    store2 = StateStore(db_path=db_path)
    assert store2.get_last_cycle_summary() == "Persisted data"
    assert store2.get_cycle_count() == 1
    store2.close()


def test_error_cycle(store: StateStore):
    """Test recording an error cycle."""
    cycle_id = store.start_cycle()
    store.finish_cycle(cycle_id, "error", "Agent SDK connection failed")

    row = store.conn.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
    assert row["status"] == "error"
    assert "connection failed" in row["summary"]


# ── Runs (Phase 2) ───────────────────────────────────────


def test_runs_table_created(store: StateStore):
    """Test that runs table is created on initialization."""
    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t["name"] for t in tables]
    assert "runs" in table_names


def test_run_lifecycle(store: StateStore):
    """Test start → finish → query lifecycle."""
    run_id = store.start_run("SP-099", pid=12345)
    assert run_id >= 1

    running = store.get_running_runs()
    assert len(running) == 1
    assert running[0]["task_id"] == "SP-099"
    assert running[0]["pid"] == 12345

    store.finish_run(run_id, exit_code=0, pr_number=42)

    running = store.get_running_runs()
    assert len(running) == 0

    run = store.get_run_by_task("SP-099")
    assert run["status"] == "success"
    assert run["exit_code"] == 0
    assert run["pr_number"] == 42
    assert run["finished_at"] is not None


def test_get_running_excludes_finished(store: StateStore):
    """Test that finished runs are excluded from running list."""
    r1 = store.start_run("SP-001", pid=111)
    store.start_run("SP-002", pid=222)
    store.finish_run(r1, exit_code=0)

    running = store.get_running_runs()
    assert len(running) == 1
    assert running[0]["task_id"] == "SP-002"


def test_consecutive_failures(store: StateStore):
    """Test consecutive failure counting."""
    assert store.get_consecutive_failures("SP-099") == 0

    # 3 consecutive failures
    for _ in range(3):
        rid = store.start_run("SP-099", pid=111)
        store.finish_run(rid, exit_code=1)

    assert store.get_consecutive_failures("SP-099") == 3


def test_consecutive_failures_reset_by_success(store: StateStore):
    """Test that a success resets the consecutive failure count."""
    for _ in range(2):
        rid = store.start_run("SP-099", pid=111)
        store.finish_run(rid, exit_code=1)

    rid = store.start_run("SP-099", pid=111)
    store.finish_run(rid, exit_code=0)

    rid = store.start_run("SP-099", pid=111)
    store.finish_run(rid, exit_code=1)

    assert store.get_consecutive_failures("SP-099") == 1


def test_mark_review_triggered(store: StateStore):
    """Test marking a run as review-triggered."""
    run_id = store.start_run("SP-099", pid=111)
    store.mark_review_triggered(run_id)

    run = store.get_run_by_task("SP-099")
    assert run["review_triggered_at"] is not None


def test_get_run_by_task_none(store: StateStore):
    """Test getting a run for a task with no runs."""
    assert store.get_run_by_task("SP-999") is None
