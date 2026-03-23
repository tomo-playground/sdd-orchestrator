"""Unit tests for StateStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.state import StateStore


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
