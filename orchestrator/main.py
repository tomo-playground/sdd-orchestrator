"""OrchestratorDaemon — main event loop for the SDD orchestrator."""

from __future__ import annotations

import asyncio
import logging
import os
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
        await self._send_startup_summary()

        while not self.stop_event.is_set():
            self.cycle += 1
            await self._heal_inconsistent_states()
            await self._run_cycle()
            await self._flush_postmerge_notifications()
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

        # notify → SlackBot 경유로 모든 알림 발송
        from orchestrator.tools.notify import init_notify

        init_notify(self.slack_bot)

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

            # done/ 태스크 ID 수집 (의존성 해소 판정용)
            from orchestrator.config import PROJECT_ROOT

            done_dir = PROJECT_ROOT / ".claude/tasks/done"
            done_ids: set[str] = set()
            if done_dir.exists():
                for entry in done_dir.iterdir():
                    if entry.is_dir() and entry.name.startswith("SP-"):
                        done_ids.add(entry.name.split("_")[0])

            running = self.state.get_running_runs()
            running_ids = {r["task_id"] for r in running}
            if len(running) >= MAX_PARALLEL_RUNS:
                return

            for task in approved:
                if task.id in running_ids:
                    continue
                if len(running) >= MAX_PARALLEL_RUNS:
                    break
                # 의존성 미완료 → 스킵
                if task.depends_on:
                    unmet = [d for d in task.depends_on if d not in done_ids]
                    if unmet:
                        logger.debug("Skip %s — unmet deps: %s", task.id, unmet)
                        continue

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

    async def _heal_inconsistent_states(self) -> None:
        """매 사이클 상태 정합성 자동 보정. 수동 개입 불필요."""
        import subprocess

        from orchestrator.config import PROJECT_ROOT, TASKS_CURRENT_DIR
        from orchestrator.tools.worktree import _has_open_pr, _update_spec_status

        if not TASKS_CURRENT_DIR.exists():
            return

        running_pids = {r["task_id"]: r["pid"] for r in self.state.get_running_runs()}
        healed = 0

        for entry in TASKS_CURRENT_DIR.iterdir():
            if not entry.is_dir() or not entry.name.startswith("SP-"):
                continue
            spec = entry / "spec.md"
            if not spec.exists():
                continue

            task_id = entry.name.split("_")[0]
            status = "unknown"
            for line in spec.read_text(errors="ignore").split("\n"):
                if line.startswith("status:"):
                    status = line.split(":", 1)[1].strip()
                    break

            pid = running_pids.get(task_id)
            pid_alive = pid and os.path.exists(f"/proc/{pid}")

            # 빈 워크트리 정리: PID 없고 커밋 0개인 워크트리 제거
            wt_dir = PROJECT_ROOT / ".claude/worktrees" / task_id
            if wt_dir.exists() and not pid_alive:
                try:
                    commits = subprocess.run(
                        ["git", "-C", str(wt_dir), "log", "--oneline", "origin/main..HEAD"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if commits.returncode == 0 and not commits.stdout.strip():
                        subprocess.run(
                            ["git", "worktree", "remove", str(wt_dir), "--force"],
                            capture_output=True,
                            timeout=10,
                            cwd=str(PROJECT_ROOT),
                        )
                        logger.info("🔧 [Heal] 빈 워크트리 삭제: %s", task_id)
                except Exception:
                    pass

            if status != "running":
                continue

            if pid_alive:
                continue  # 정상 실행 중

            has_pr = _has_open_pr(task_id)
            if has_pr:
                continue  # PR 있으면 running 유지 (리뷰 대기)

            # 좀비 감지 → 자동 복원
            _update_spec_status(task_id, "approved")
            logger.warning("🔧 [Heal] %s: running → approved (no alive PID, no open PR)", task_id)
            healed += 1

        if healed:
            # 자동 커밋 (main에서만)
            try:
                subprocess.run(
                    ["git", "add", ".claude/tasks/current/"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"chore: 상태 자동 보정 — {healed}건 running → approved",
                    ],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["git", "push"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    timeout=15,
                )
                logger.info("🔧 [Heal] %d건 자동 보정 커밋+푸시 완료", healed)
            except Exception:
                logger.warning("🔧 [Heal] 커밋/푸시 실패", exc_info=True)

    async def _flush_postmerge_notifications(self) -> None:
        """Send post-merge DoD notifications from sdd-sync to Slack."""
        import glob

        from orchestrator.tools.notify import do_notify_human

        for path in glob.glob("/tmp/sdd-postmerge-SP-*.notify"):
            try:
                msg = open(path).read().strip()  # noqa: SIM115
                if msg:
                    await do_notify_human({"message": msg, "level": "warning"})
                    logger.info("Post-merge notification sent: %s", path)
                os.remove(path)
            except Exception:
                logger.warning("Failed to send post-merge notification: %s", path, exc_info=True)

    async def _send_startup_summary(self) -> None:
        """Send concise startup summary to Slack."""
        import subprocess

        from orchestrator.config import MAX_PARALLEL_RUNS, PROJECT_ROOT
        from orchestrator.tools.notify import do_notify_human

        try:
            # Running tasks
            running = self.state.get_running_runs()
            running_names = [r["task_id"] for r in running]

            # Approved (waiting) tasks
            from orchestrator.tools.backlog import parse_backlog

            tasks = parse_backlog()
            approved = [t for t in tasks if t.spec_status == "approved"]

            # Open PRs
            r = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "open",
                    "--json",
                    "number,title",
                    "--jq",
                    '.[] | "#\\(.number)(\\(.title | split(" ") | .[0]))"',
                ],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(PROJECT_ROOT),
            )
            prs = r.stdout.strip().split("\n") if r.returncode == 0 and r.stdout.strip() else []

            # Build message
            slot_str = f"{len(running)}/{MAX_PARALLEL_RUNS}"
            running_str = ", ".join(running_names) if running_names else "없음"
            waiting_str = (
                f"{', '.join(t.id for t in approved[:3])} 외 {len(approved) - 3}건"
                if len(approved) > 3
                else ", ".join(t.id for t in approved) or "없음"
            )
            pr_str = (
                f"{', '.join(prs[:3])} 외 {len(prs) - 3}건"
                if len(prs) > 3
                else ", ".join(prs) or "없음"
            )

            msg = (
                f"🔄 Coding Machine 재기동\n\n"
                f"슬롯: {slot_str} ({running_str})\n"
                f"대기: {waiting_str}\n"
                f"PR: {pr_str}\n\n"
                f"명령: /status, /merge #N, /kill SP-NNN"
            )
            await do_notify_human({"message": msg, "level": "info"})
        except Exception:
            logger.warning("Startup summary failed", exc_info=True)

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
            "rollbacks": [],
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
                    if not entry.is_dir() or not entry.name.startswith("SP-"):
                        continue
                    spec = entry / "spec.md"
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

            # Rollback history
            summary["rollbacks"] = self.state.get_recent_rollbacks(hours=24)
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
