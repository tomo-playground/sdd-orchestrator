"""SQLite-based state store for orchestrator cycles and decisions."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sdd_orchestrator.config import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class StateStore:
    """Persistent state for orchestrator cycles and decision logs."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
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
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                pid INTEGER,
                status TEXT NOT NULL DEFAULT 'running',
                exit_code INTEGER,
                pr_number INTEGER,
                review_triggered_at TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS rollbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_pr INTEGER NOT NULL,
                revert_pr INTEGER,
                error_count INTEGER NOT NULL,
                baseline_count INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'monitoring',
                created_at TEXT NOT NULL,
                finished_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rollbacks_original_pr
            ON rollbacks(original_pr);
            CREATE TABLE IF NOT EXISTS task_status (
                task_id   TEXT PRIMARY KEY,
                status    TEXT NOT NULL DEFAULT 'pending',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approval_attempts (
                task_id TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
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
            "INSERT INTO decision_log (cycle_id, action, target, reason, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (cycle_id, action, target, reason, now),
        )
        self.conn.commit()

    # ── Runs (Phase 2) ──────────────────────────────────────

    def start_run(self, task_id: str, pid: int | None = None) -> int:
        """Record a new worktree run. Returns the run ID."""
        now = datetime.now(UTC).isoformat()
        cur = self.conn.execute(
            "INSERT INTO runs (task_id, pid, status, started_at) VALUES (?, ?, 'running', ?)",
            (task_id, pid, now),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def finish_run(self, run_id: int, exit_code: int, pr_number: int | None = None) -> None:
        """Mark a run as finished with exit code."""
        now = datetime.now(UTC).isoformat()
        status = "success" if exit_code == 0 else "failed"
        self.conn.execute(
            "UPDATE runs SET status = ?, exit_code = ?, pr_number = ?, finished_at = ?"
            " WHERE id = ?",
            (status, exit_code, pr_number, now, run_id),
        )
        self.conn.commit()

    def get_running_runs(self) -> list[dict]:
        """Get all runs with status='running'."""
        rows = self.conn.execute(
            "SELECT id, task_id, pid, started_at FROM runs WHERE status = 'running'"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_consecutive_failures(self, task_id: str) -> int:
        """Count consecutive failed runs for a task (from most recent)."""
        rows = self.conn.execute(
            "SELECT status FROM runs WHERE task_id = ? ORDER BY id DESC",
            (task_id,),
        ).fetchall()
        count = 0
        for row in rows:
            if row["status"] == "failed":
                count += 1
            else:
                break
        return count

    def mark_review_triggered(self, run_id: int) -> None:
        """Record that claude-fix was triggered for this run."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            "UPDATE runs SET review_triggered_at = ? WHERE id = ?",
            (now, run_id),
        )
        self.conn.commit()

    def get_run_by_task(self, task_id: str) -> dict | None:
        """Get the most recent run for a task."""
        row = self.conn.execute(
            "SELECT * FROM runs WHERE task_id = ? ORDER BY id DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        return dict(row) if row else None

    # ── Rollbacks ─────────────────────────────────────────

    def record_rollback(
        self,
        original_pr: int,
        error_count: int,
        baseline_count: int,
        *,
        revert_pr: int | None = None,
        status: str = "monitoring",
    ) -> int | None:
        """Record a rollback entry. Returns the rollback ID, or None if duplicate."""
        now = datetime.now(UTC).isoformat()
        try:
            cur = self.conn.execute(
                "INSERT INTO rollbacks"
                " (original_pr, revert_pr, error_count, baseline_count, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (original_pr, revert_pr, error_count, baseline_count, status, now),
            )
            self.conn.commit()
            return cur.lastrowid  # type: ignore[return-value]
        except sqlite3.IntegrityError:
            logger.info("Duplicate rollback for PR #%d, skipping", original_pr)
            return None

    def update_rollback_status(
        self, rollback_id: int, status: str, *, revert_pr: int | None = None
    ) -> None:
        """Update rollback status and optionally set revert_pr."""
        now = datetime.now(UTC).isoformat()
        if revert_pr is not None:
            self.conn.execute(
                "UPDATE rollbacks SET status = ?, revert_pr = ?, finished_at = ? WHERE id = ?",
                (status, revert_pr, now, rollback_id),
            )
        else:
            self.conn.execute(
                "UPDATE rollbacks SET status = ?, finished_at = ? WHERE id = ?",
                (status, now, rollback_id),
            )
        self.conn.commit()

    def update_rollback_baseline(self, rollback_id: int, baseline_count: int) -> None:
        """Update the baseline error count for a rollback entry."""
        self.conn.execute(
            "UPDATE rollbacks SET baseline_count = ? WHERE id = ?",
            (baseline_count, rollback_id),
        )
        self.conn.commit()

    def update_rollback_surge(self, rollback_id: int, error_count: int) -> None:
        """Mark a rollback as surge_detected with the current error count.

        Note: finished_at is NOT set here — surge_detected is an intermediate state.
        Terminal states (reverted, revert_failed) set finished_at via update_rollback_status.
        """
        self.conn.execute(
            "UPDATE rollbacks SET error_count = ?, status = 'surge_detected' WHERE id = ?",
            (error_count, rollback_id),
        )
        self.conn.commit()

    def has_rollback(self, original_pr: int) -> bool:
        """Check if a rollback already exists for a PR."""
        row = self.conn.execute(
            "SELECT 1 FROM rollbacks WHERE original_pr = ? LIMIT 1",
            (original_pr,),
        ).fetchone()
        return row is not None

    def get_recent_rollbacks(self, hours: int = 24) -> list[dict]:
        """Get rollbacks within the last N hours."""
        # Simple approach: fetch all and filter in Python (small table)
        rows = self.conn.execute("SELECT * FROM rollbacks ORDER BY id DESC LIMIT 50").fetchall()
        from datetime import timedelta

        cutoff_dt = datetime.now(UTC) - timedelta(hours=hours)
        results = []
        for row in rows:
            try:
                created = datetime.fromisoformat(row["created_at"])
                if created >= cutoff_dt:
                    results.append(dict(row))
            except (ValueError, KeyError):
                logger.warning("Rollback row id=%s has unparseable created_at, skipping", row["id"])
        return results

    # ── Cycles ────────────────────────────────────────────

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

    # ── Task Status ────────────────────────────────────────

    def get_task_status(self, task_id: str) -> str:
        """Get task lifecycle status from DB. Returns 'pending' if not found."""
        row = self.conn.execute(
            "SELECT status FROM task_status WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["status"] if row else "pending"

    def set_task_status(self, task_id: str, status: str) -> None:
        """Upsert task status. updated_at is set automatically."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO task_status (task_id, status, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(task_id) DO UPDATE SET status = excluded.status,"
            " updated_at = excluded.updated_at",
            (task_id, status, now),
        )
        self.conn.commit()

    def get_all_task_statuses(self) -> dict[str, str]:
        """Return all task statuses as {task_id: status}."""
        rows = self.conn.execute("SELECT task_id, status FROM task_status").fetchall()
        return {row["task_id"]: row["status"] for row in rows}

    def migrate_spec_status_to_db(self) -> int:
        """One-time: seed task_status from current/ and done/ spec.md files.

        Only inserts if the task_id does not already exist in DB.
        Returns the number of tasks migrated.
        """
        from sdd_orchestrator.config import TASKS_CURRENT_DIR, TASKS_DONE_DIR

        migrated = 0

        # Scan current/ tasks — default to "pending" (state.db is SSOT, no spec.md status)
        if TASKS_CURRENT_DIR.exists():
            for spec in TASKS_CURRENT_DIR.glob("SP-*_*/spec.md"):
                task_id = spec.parent.name.split("_")[0]
                existing = self.conn.execute(
                    "SELECT 1 FROM task_status WHERE task_id = ?", (task_id,)
                ).fetchone()
                if existing:
                    continue
                self.set_task_status(task_id, "pending")
                migrated += 1
                logger.info("Migrated %s status=pending (new task) to DB", task_id)

        # Scan done/ tasks — always "done" (location is authoritative)
        if TASKS_DONE_DIR.exists():
            for task_dir in TASKS_DONE_DIR.glob("SP-*_*/"):
                task_id = task_dir.name.split("_")[0]
                existing = self.conn.execute(
                    "SELECT 1 FROM task_status WHERE task_id = ?", (task_id,)
                ).fetchone()
                if existing:
                    continue
                self.set_task_status(task_id, "done")
                migrated += 1
                logger.info("Migrated %s status=done from done/ to DB", task_id)

        return migrated

    def delete_task_status(self, task_id: str) -> None:
        """Remove a task status row (used for rollback on creation failure)."""
        self.conn.execute("DELETE FROM task_status WHERE task_id = ?", (task_id,))
        self.conn.commit()

    # ── Approval Attempts (SP-130) ────────────────────────

    def get_approval_attempts(self, task_id: str) -> int:
        """Get the number of auto-approval retry attempts for a task."""
        row = self.conn.execute(
            "SELECT attempts FROM approval_attempts WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return row["attempts"] if row else 0

    def increment_approval_attempts(self, task_id: str) -> int:
        """Increment and return the approval attempt count."""
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO approval_attempts (task_id, attempts, updated_at)"
            " VALUES (?, 1, ?)"
            " ON CONFLICT(task_id) DO UPDATE SET"
            " attempts = approval_attempts.attempts + 1,"
            " updated_at = excluded.updated_at",
            (task_id, now),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT attempts FROM approval_attempts WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return row["attempts"]

    def close(self) -> None:
        """Commit and close the database connection."""
        try:
            self.conn.commit()
            self.conn.close()
            logger.info("State store closed")
        except sqlite3.Error as e:
            logger.error("Error closing state store: %s", e)
