"""OrchestratorDaemon — main event loop for the SDD orchestrator."""

from __future__ import annotations

import asyncio
import logging
import shutil
import signal
import sys
from pathlib import Path

from orchestrator.agents import build_cycle_prompt, create_lead_agent_options
from orchestrator.config import (
    AGENT_QUERY_TIMEOUT,
    BACKLOG_PATH,
    CYCLE_INTERVAL,
    DEFAULT_DB_PATH,
)
from orchestrator.state import StateStore
from orchestrator.tools import create_orchestrator_mcp_server
from orchestrator.utils import query_agent

logger = logging.getLogger(__name__)


class OrchestratorDaemon:
    """Main daemon that runs the orchestrator event loop."""

    def __init__(self, interval: int = CYCLE_INTERVAL, db_path: Path = DEFAULT_DB_PATH):
        from orchestrator.tools.worktree import set_state_store

        self.interval = interval
        self.cycle = 0
        self.stop_event = asyncio.Event()
        self.state = StateStore(db_path=db_path)
        set_state_store(self.state)
        self.mcp_server = create_orchestrator_mcp_server()
        self._last_report_date: str | None = None

    async def run(self) -> None:
        """Start the orchestrator event loop."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_signal)

        self._preflight_check()
        logger.info("Orchestrator started (interval=%ds)", self.interval)

        while not self.stop_event.is_set():
            self.cycle += 1
            await self._run_cycle()
            await self._maybe_send_daily_report()

            if self.interval <= 0:
                break  # Single-cycle mode for testing

            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.interval)
            except TimeoutError:
                pass  # Normal — next cycle

        self.state.close()
        logger.info("Shutdown complete")

    def _handle_signal(self) -> None:
        logger.info("Received shutdown signal")
        self.stop_event.set()

    def _preflight_check(self) -> None:
        """Verify prerequisites before starting (fail-fast)."""
        from orchestrator.config import SENTRY_AUTH_TOKEN, SLACK_WEBHOOK_URL

        # 1. gh CLI installed and authenticated
        if not shutil.which("gh"):
            logger.error("gh CLI not found. Install: https://cli.github.com/")
            sys.exit(1)

        # 2. backlog.md exists
        if not BACKLOG_PATH.exists():
            logger.error("backlog.md not found at %s", BACKLOG_PATH)
            sys.exit(1)

        # 3. Optional: Sentry token
        if not SENTRY_AUTH_TOKEN:
            logger.warning("SENTRY_AUTH_TOKEN not set — sentry_scan will be disabled")

        # 4. Optional: Slack webhook
        if not SLACK_WEBHOOK_URL:
            logger.warning("SLACK_WEBHOOK_URL not set — notifications will be log-only")

        logger.info("Preflight check passed")

    async def _run_cycle(self) -> None:
        """Execute a single orchestrator cycle."""
        cycle_id = self.state.start_cycle()
        logger.info("=== Cycle #%d started (db_id=%d) ===", self.cycle, cycle_id)

        try:
            options = create_lead_agent_options(self.mcp_server)
            prev_summary = self.state.get_last_cycle_summary()
            prompt = build_cycle_prompt(self.cycle, prev_summary)

            response_text = await asyncio.wait_for(
                query_agent(options, prompt), timeout=AGENT_QUERY_TIMEOUT
            )

            self.state.log_decision(
                cycle_id,
                "scan",
                None,
                f"Cycle #{self.cycle} completed — {len(response_text)} chars",
            )
            self.state.finish_cycle(cycle_id, "success", response_text)
            logger.info("=== Cycle #%d completed ===", self.cycle)

        except Exception as e:
            logger.exception("Cycle #%d failed", self.cycle)
            self.state.finish_cycle(cycle_id, "error", str(e))

    async def _maybe_send_daily_report(self) -> None:
        """Send daily report once per day at 00:00 UTC (09:00 KST)."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")

        if self._last_report_date == today:
            return

        # Only send after 00:00 UTC (09:00 KST)
        if now.hour < 0:
            return

        try:
            from orchestrator.tools.notify import send_daily_report

            summary = {
                "completed_prs": [],
                "in_progress": [],
                "blockers": [],
                "sentry_issues": {"open": 0, "autofix_prs": 0},
            }
            # Best-effort: gather from last cycle summary
            last_summary = self.state.get_last_cycle_summary()
            if last_summary:
                summary["in_progress"].append(f"Last cycle: {last_summary[:100]}")

            await send_daily_report(summary)
            self._last_report_date = today
            logger.info("Daily report sent for %s", today)
        except Exception:
            logger.exception("Failed to send daily report")


def _setup_logging() -> None:
    """Configure logging for daemon mode."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def cli_entry() -> None:
    """CLI entry point for `python -m orchestrator`."""
    _setup_logging()
    daemon = OrchestratorDaemon()
    asyncio.run(daemon.run())
