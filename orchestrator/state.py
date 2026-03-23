"""SQLite-based state store for orchestrator cycles and decisions."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from orchestrator.config import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class StateStore:
    """Persistent state for orchestrator cycles and decision logs."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                summary TEXT
            );
            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER REFERENCES cycles(id),
                action TEXT NOT NULL,
                target TEXT,
                reason TEXT,
                created_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def start_cycle(self) -> int:
        """Record a new cycle start. Returns the cycle ID."""
        now = datetime.now(UTC).isoformat()
        cur = self.conn.execute(
            "INSERT INTO cycles (started_at, status) VALUES (?, 'running')",
            (now,),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def finish_cycle(self, cycle_id: int, status: str, summary: str) -> None:
        """Mark a cycle as finished with status and summary."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            "UPDATE cycles SET finished_at = ?, status = ?, summary = ? WHERE id = ?",
            (now, status, summary, cycle_id),
        )
        self.conn.commit()

    def log_decision(self, cycle_id: int, action: str, target: str | None, reason: str) -> None:
        """Record a decision made during a cycle."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO decision_log (cycle_id, action, target, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (cycle_id, action, target, reason, now),
        )
        self.conn.commit()

    def get_last_cycle_summary(self) -> str | None:
        """Get the summary from the most recent completed cycle."""
        row = self.conn.execute(
            "SELECT summary FROM cycles WHERE status != 'running' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["summary"] if row else None

    def get_cycle_count(self) -> int:
        """Get total number of cycles recorded."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM cycles").fetchone()
        return row["cnt"]

    def close(self) -> None:
        """Commit and close the database connection."""
        try:
            self.conn.commit()
            self.conn.close()
            logger.info("State store closed")
        except sqlite3.Error as e:
            logger.error("Error closing state store: %s", e)
