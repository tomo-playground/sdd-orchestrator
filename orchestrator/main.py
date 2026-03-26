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
    MAX_PARALLEL_RUNS,
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
        self.pause_event = asyncio.Event()  # set = paused, clear = running
        self.state = StateStore(db_path=db_path)
        set_state_store(self.state)
        self.mcp_server = create_orchestrator_mcp_server()
        self._last_report_date: str | None = None
        self.slack_bot = None
        self._slack_bot_task: asyncio.Task | None = None
        self._notify_task: asyncio.Task | None = None

    async def run(self) -> None:
        """Start the orchestrator event loop."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_signal)

        self._preflight_check()
        await self._maybe_start_slack_bot()
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

        await self._stop_slack_bot()
        self.state.close()
        logger.info("Shutdown complete")

    def _handle_signal(self) -> None:
        logger.info("Received shutdown signal")
        self.stop_event.set()

    def _preflight_check(self) -> None:
        """Verify prerequisites before starting (fail-fast)."""
        from orchestrator.config import SENTRY_AUTH_TOKEN, SLACK_BOT_TOKEN

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

        # 4. Optional: Slack Bot token
        if not SLACK_BOT_TOKEN:
            logger.warning("SLACK_BOT_TOKEN not set — notifications will be log-only")

        logger.info("Preflight check passed")

    async def _maybe_start_slack_bot(self) -> None:
        """Start Slack Bot listener if tokens are configured."""
        from orchestrator.config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN

        if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
            logger.info("Slack Bot tokens not set — bot listener disabled")
            return

        from orchestrator.tools.slack_bot import SlackBotListener, set_daemon

        set_daemon(self)
        self.slack_bot = SlackBotListener(mcp_server=self.mcp_server)
        self._slack_bot_task = asyncio.create_task(self._run_slack_bot_with_restart())

    async def _run_slack_bot_with_restart(self) -> None:
        """Run Slack Bot with auto-restart on crash (max 3 attempts)."""
        restart_count = 0
        max_restarts = 3
        while restart_count < max_restarts and not self.stop_event.is_set():
            try:
                await self.slack_bot.start()
                await self.stop_event.wait()
            except Exception:
                restart_count += 1
                try:
                    await self.slack_bot.stop()
                except Exception:
                    pass
                logger.warning(
                    "SlackBot crashed (%d/%d), restart in 30s", restart_count, max_restarts
                )
                await asyncio.sleep(30)
        if restart_count >= max_restarts:
            logger.error("SlackBot failed %d times, giving up", max_restarts)
            # Notify via log (Bot is dead, can't use Bot itself)
            from orchestrator.tools.notify import do_notify_human

            self._notify_task = asyncio.create_task(
                do_notify_human(
                    {
                        "message": f"[SlackBot] {max_restarts}회 재시작 실패 — 수동 점검 필요",
                        "level": "critical",
                    }
                )
            )

    async def _stop_slack_bot(self) -> None:
        """Stop Slack Bot listener if running."""
        if self._slack_bot_task and not self._slack_bot_task.done():
            self._slack_bot_task.cancel()
            try:
                await self._slack_bot_task
            except asyncio.CancelledError:
                pass
        if self.slack_bot:
            try:
                await self.slack_bot.stop()
            except Exception:
                logger.exception("Error stopping SlackBot")

    async def _run_cycle(self) -> None:
        """Execute a single orchestrator cycle."""
        if self.pause_event.is_set():
            logger.info("Paused, skipping cycle")
            return

        # Deterministic: auto-launch approved tasks before LLM cycle
        await self._auto_launch_approved()

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

    async def _auto_launch_approved(self) -> None:
        """Deterministic auto-launch: approved tasks with available slots.

        This runs BEFORE the LLM cycle to ensure approved tasks are launched
        without relying on LLM judgment.
        """
        from orchestrator.config import ENABLE_AUTO_RUN
        from orchestrator.tools.backlog import parse_backlog
        from orchestrator.tools.worktree import do_launch_sdd_run

        if not ENABLE_AUTO_RUN:
            return

        try:
            tasks = parse_backlog()
            approved = [t for t in tasks if t.spec_status == "approved"]
            if not approved:
                return

            running = self.state.get_running_runs()
            running_ids = {r["task_id"] for r in running}
            if len(running) >= MAX_PARALLEL_RUNS:
                return

            for task in approved:
                if task.id in running_ids:
                    continue
                if len(running) >= MAX_PARALLEL_RUNS:
                    break

                logger.info("Auto-launching approved task: %s", task.id)
                result = await do_launch_sdd_run(task.id)
                is_error = result.get("isError", False)
                msg = result.get("content", [{}])[0].get("text", "")
                if is_error:
                    logger.warning("Auto-launch %s failed: %s", task.id, msg)
                else:
                    logger.info("Auto-launch %s: %s", task.id, msg)
                    running = self.state.get_running_runs()
                    running_ids = {r["task_id"] for r in running}
        except Exception:
            logger.exception("Auto-launch check failed")

    async def _maybe_send_daily_report(self) -> None:
        """Send daily report once per day at 00:00 UTC (09:00 KST)."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")

        if self._last_report_date == today:
            return

        if now.hour < 0:
            return

        try:
            from orchestrator.tools.notify import send_daily_report

            summary = await self._gather_daily_summary()
            await send_daily_report(summary)
            self._last_report_date = today
            logger.info("Daily report sent for %s", today)
        except Exception:
            logger.exception("Failed to send daily report")

    async def _gather_daily_summary(self) -> dict:
        """실제 데이터를 수집하여 데일리 리포트 요약을 구성한다."""
        import subprocess

        from orchestrator.config import MAX_PARALLEL_RUNS, TASKS_CURRENT_DIR

        project_dir = str(self.state.db_path.parent.parent)
        summary: dict = {
            "completed_prs": [],
            "in_progress": [],
            "blockers": [],
            "open_prs": [],
            "slots": "0/0",
            "sentry_issues": {"open": 0, "autofix_prs": 0},
        }
        try:
            # 머지된 PR (최근 5개)
            r = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "merged",
                    "--base",
                    "main",
                    "--limit",
                    "5",
                    "--json",
                    "number,title",
                    "--jq",
                    '.[] | "#\\(.number) \\(.title)"',
                ],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=project_dir,
            )
            if r.returncode == 0 and r.stdout.strip():
                summary["completed_prs"] = r.stdout.strip().split("\n")

            # 열린 PR
            r = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "open",
                    "--base",
                    "main",
                    "--json",
                    "number,title,reviewDecision",
                    "--jq",
                    '.[] | "#\\(.number) \\(.title) [\\(.reviewDecision // "PENDING")]"',
                ],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=project_dir,
            )
            if r.returncode == 0 and r.stdout.strip():
                summary["open_prs"] = r.stdout.strip().split("\n")

            # 진행 중 태스크
            if TASKS_CURRENT_DIR.exists():
                for entry in sorted(TASKS_CURRENT_DIR.iterdir()):
                    spec = entry / "spec.md" if entry.is_dir() else entry
                    if not spec.exists():
                        continue
                    sp_id = entry.name.split("_")[0]
                    status = "unknown"
                    for line in spec.read_text(errors="ignore").split("\n"):
                        if line.startswith("status:"):
                            status = line.split(":", 1)[1].strip()
                            break
                    summary["in_progress"].append(f"{sp_id} ({status})")

            # 슬롯 현황
            r = subprocess.run(
                ["pgrep", "-f", "claude.*--worktree"], capture_output=True, text=True
            )
            used = len(r.stdout.strip().split("\n")) if r.stdout.strip() else 0
            summary["slots"] = f"{used}/{MAX_PARALLEL_RUNS}"

            # Sentry 이슈
            r = subprocess.run(
                [
                    "gh",
                    "issue",
                    "list",
                    "--label",
                    "sentry",
                    "--state",
                    "open",
                    "--json",
                    "number",
                    "--jq",
                    "length",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=project_dir,
            )
            if r.returncode == 0 and r.stdout.strip():
                summary["sentry_issues"]["open"] = int(r.stdout.strip())
        except Exception as e:
            logger.warning("Daily summary gather error: %s", e)

        return summary


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
