"""Slack Bot listener — Socket Mode event handling + command dispatch."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING

from orchestrator.config import (
    SLACK_BOT_ALLOWED_CHANNEL,
    SLACK_BOT_ALLOWED_USERS,
    SLACK_BOT_CHAT_INTERVAL,
    SLACK_BOT_TOKEN,
)

if TYPE_CHECKING:
    from slack_bolt.async_app import AsyncApp
    from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)

_READ_COMMANDS = {"상태", "백로그"}

SP_RE = re.compile(r"SP-(\d+)")
PR_RE = re.compile(r"#(\d+)")


class SlackBotListener:
    """Socket Mode listener that receives Slack mentions and dispatches commands."""

    def __init__(self, daemon: object) -> None:
        self.daemon = daemon
        self._cmd_lock = asyncio.Lock()
        self._post_lock = asyncio.Lock()
        self._last_post: float = 0
        self.handler: object | None = None
        self.app: AsyncApp | None = None
        self.web_client: AsyncWebClient | None = None

    async def start(self) -> None:
        """Connect via Socket Mode (non-blocking WebSocket)."""
        from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
        from slack_bolt.async_app import AsyncApp

        from orchestrator.config import SLACK_APP_TOKEN, SLACK_BOT_API_TIMEOUT

        self.app = AsyncApp(token=SLACK_BOT_TOKEN)
        self.app.event("app_mention")(self._handle_mention)
        self.web_client = self.app.client
        self.web_client.timeout = SLACK_BOT_API_TIMEOUT

        self.handler = AsyncSocketModeHandler(self.app, SLACK_APP_TOKEN)
        await self.handler.connect_async()
        logger.info("SlackBot connected via Socket Mode")

    async def stop(self) -> None:
        """Disconnect gracefully."""
        if self.handler:
            await self.handler.disconnect_async()
            logger.info("SlackBot disconnected")

    # ── Event handler ────────────────────────────────────────

    async def _handle_mention(self, event: dict, say) -> None:
        """Handle app_mention events."""
        if event.get("bot_id"):
            return

        channel = event.get("channel", "")
        user_id = event.get("user", "")
        thread_ts = event.get("ts", "")
        text = event.get("text", "")

        # Strip bot mention (<@UXXXXXXXX>)
        text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()

        # Channel allowlist — silently ignore unauthorized channels
        if not self._is_allowed_channel(channel):
            logger.warning(
                "Ignored event from channel=%s (allowed=%s)", channel, SLACK_BOT_ALLOWED_CHANNEL
            )
            return

        # User allowlist — deny commands from unauthorized users
        if not self._is_allowed_user(user_id):
            await self._post_message(
                channel,
                _error_blocks("권한 없음: 이 명령을 실행할 권한이 없습니다."),
                thread_ts,
            )
            return

        cmd_key = self._parse_cmd_key(text)
        if cmd_key in _READ_COMMANDS:
            blocks = await self._dispatch_command(text, cmd_key)
        else:
            async with self._cmd_lock:
                blocks = await self._dispatch_command(text, cmd_key)

        await self._post_message(channel, blocks, thread_ts)

    @staticmethod
    def _is_allowed_channel(channel: str) -> bool:
        """Return True if channel is in allowlist (empty = all allowed)."""
        if not SLACK_BOT_ALLOWED_CHANNEL:
            return True
        return channel == SLACK_BOT_ALLOWED_CHANNEL

    @staticmethod
    def _is_allowed_user(user_id: str) -> bool:
        """Return True if user is in allowlist (empty = all allowed)."""
        if not SLACK_BOT_ALLOWED_USERS:
            return True
        allowed = {u.strip() for u in SLACK_BOT_ALLOWED_USERS.split(",") if u.strip()}
        return not allowed or user_id in allowed

    # ── Command parsing ──────────────────────────────────────

    @staticmethod
    def _parse_cmd_key(text: str) -> str:
        """Extract the command keyword from user text."""
        text_lower = text.strip().lower()
        if text_lower.startswith("상태"):
            return "상태"
        if text_lower.startswith("실행"):
            return "실행"
        if text_lower.startswith("머지"):
            return "머지"
        if text_lower.startswith("중지"):
            return "중지"
        if text_lower.startswith("시작"):
            return "시작"
        if text_lower.startswith("백로그"):
            return "백로그"
        return "help"

    async def _dispatch_command(self, text: str, cmd_key: str) -> list[dict]:
        """Route to the correct handler and return Block Kit blocks."""
        try:
            if cmd_key == "상태":
                return await self._cmd_status()
            if cmd_key == "실행":
                return await self._cmd_launch(text)
            if cmd_key == "머지":
                return await self._cmd_merge(text)
            if cmd_key == "중지":
                return self._cmd_pause()
            if cmd_key == "시작":
                return self._cmd_resume()
            if cmd_key == "백로그":
                return await self._cmd_backlog()
            return self._cmd_help()
        except Exception:
            logger.exception("Command execution failed: %s", text)
            return _error_blocks("명령 실행 중 오류가 발생했습니다.")

    # ── Command implementations ──────────────────────────────

    async def _cmd_status(self) -> list[dict]:
        """Show current tasks, PRs, and worktrees."""
        # current/ 디렉토리에서 직접 태스크 수집
        from orchestrator.config import TASKS_CURRENT_DIR
        from orchestrator.tools.backlog import BacklogTask
        from orchestrator.tools.github import _run_gh_command, summarize_prs
        from orchestrator.tools.worktree import do_check_running_worktrees

        current: list[BacklogTask] = []
        if TASKS_CURRENT_DIR.exists():
            for spec in sorted(TASKS_CURRENT_DIR.glob("SP-*/spec.md")):
                import re as _re

                content = spec.read_text(encoding="utf-8")
                id_m = _re.search(r"^id:\s*(SP-\d+)", content, _re.MULTILINE)
                status_m = _re.search(r"^status:\s*(\w+)", content, _re.MULTILINE)
                if not id_m:
                    continue
                desc = (
                    spec.parent.name.split("_", 1)[1].replace("-", " ")
                    if "_" in spec.parent.name
                    else ""
                )
                current.append(
                    BacklogTask(
                        id=id_m.group(1),
                        priority="",
                        description=desc[:40],
                        spec_status=status_m.group(1) if status_m else "unknown",
                    )
                )

        pr_result = await _run_gh_command(
            "pr",
            "list",
            "--state",
            "open",
            "--json",
            "number,title,headRefName,state,reviewDecision,statusCheckRollup,labels",
        )
        prs: list | None = None  # None signals fetch error
        if not pr_result.get("isError") and "data" in pr_result:
            prs = summarize_prs(pr_result.get("data", []))

        wt_result = await do_check_running_worktrees()
        running: list | None = None  # None signals fetch error
        if not wt_result.get("isError"):
            wt_text = wt_result.get("content", [{}])[0].get("text", "[]")
            running = _safe_json_loads(wt_text, [])

        # Build blocks
        task_lines = []
        for t in current[:5]:
            task_lines.append(f"• `{t.id}` ({t.spec_status}) — {t.description[:40]}")
        task_text = "\n".join(task_lines) if task_lines else "— 없음"

        if prs is None:
            pr_text = ":warning: PR 조회 실패 (gh API 오류)"
        else:
            pr_lines = []
            for p in prs[:5]:
                pr_lines.append(
                    f"• `#{p['number']}` {p['title'][:30]} "
                    f"[CI: {p['ci_status']}] [Review: {p['review'] or 'none'}]"
                )
            pr_text = "\n".join(pr_lines) if pr_lines else "— 없음"

        if running is None:
            run_text = ":warning: 워크트리 조회 실패"
        else:
            run_lines = []
            for r in running[:3]:
                run_lines.append(f"• `{r.get('task_id', '?')}` (pid={r.get('pid', '?')})")
            run_text = "\n".join(run_lines) if run_lines else "— 없음"

        return [
            _header_block("현재 상태"),
            _section_block(f"*태스크*\n{task_text}"),
            _section_block(f"*Pull Requests*\n{pr_text}"),
            _section_block(f"*실행 중 워크트리*\n{run_text}"),
        ]

    async def _cmd_launch(self, text: str) -> list[dict]:
        """Launch /sdd-run for a task."""
        from orchestrator.tools.worktree import do_launch_sdd_run

        sp_match = SP_RE.search(text)
        if not sp_match:
            return _error_blocks("태스크 ID가 필요합니다. 예: `실행 SP-077`")

        sp_id = f"SP-{sp_match.group(1)}"
        result = await do_launch_sdd_run(sp_id)
        result_text = result.get("content", [{}])[0].get("text", "")

        if result.get("isError"):
            return _error_blocks(result_text)

        return [
            _header_block("실행 시작"),
            _section_block(f"`{sp_id}` 워크트리를 기동했습니다.\n{result_text}"),
        ]

    async def _cmd_merge(self, text: str) -> list[dict]:
        """Merge a PR."""
        from orchestrator.tools.github import do_merge_pr

        pr_match = PR_RE.search(text)
        if not pr_match:
            return _error_blocks("PR 번호가 필요합니다. 예: `머지 #177`")

        pr_number = int(pr_match.group(1))
        result = await do_merge_pr(pr_number)
        result_text = result.get("content", [{}])[0].get("text", "")

        if result.get("isError"):
            return _error_blocks(result_text)

        return [
            _header_block("머지 완료"),
            _section_block(f"PR `#{pr_number}` — {result_text}"),
        ]

    def _cmd_pause(self) -> list[dict]:
        """Pause the orchestrator cycle."""
        if hasattr(self.daemon, "pause_event"):
            self.daemon.pause_event.set()
        return [
            _header_block("일시정지"),
            _section_block(
                "오케스트레이터 사이클을 일시정지했습니다.\n`시작` 명령으로 재개할 수 있습니다."
            ),
        ]

    def _cmd_resume(self) -> list[dict]:
        """Resume the orchestrator cycle."""
        if hasattr(self.daemon, "pause_event"):
            self.daemon.pause_event.clear()
        return [
            _header_block("재개"),
            _section_block("오케스트레이터 사이클을 재개했습니다."),
        ]

    async def _cmd_backlog(self) -> list[dict]:
        """Show top 5 backlog items."""
        from orchestrator.tools.backlog import parse_backlog

        tasks = parse_backlog()
        top5 = tasks[:5]

        lines = []
        for t in top5:
            deps = f" (depends: {', '.join(t.depends_on)})" if t.depends_on else ""
            lines.append(f"• `{t.id}` [{t.priority}] {t.description[:40]}{deps}")

        text = "\n".join(lines) if lines else "— 백로그가 비어 있습니다"
        return [
            _header_block("백로그 (상위 5개)"),
            _section_block(text),
        ]

    @staticmethod
    def _cmd_help() -> list[dict]:
        """Show available commands."""
        return [
            _header_block("사용 가능한 명령"),
            _section_block(
                "• `상태` — 현재 태스크/PR/워크트리 상태\n"
                "• `실행 SP-NNN` — SDD 태스크 실행\n"
                "• `머지 #NNN` — PR 머지\n"
                "• `중지` — 오케스트레이터 일시정지\n"
                "• `시작` — 오케스트레이터 재개\n"
                "• `백로그` — 대기 태스크 상위 5개"
            ),
        ]

    # ── Message posting ──────────────────────────────────────

    async def _post_message(
        self,
        channel: str,
        blocks: list[dict],
        thread_ts: str | None = None,
    ) -> None:
        """Post a Block Kit message with rate limiting."""
        if not self.web_client:
            return

        async with self._post_lock:
            elapsed = time.monotonic() - self._last_post
            if elapsed < SLACK_BOT_CHAT_INTERVAL:
                await asyncio.sleep(SLACK_BOT_CHAT_INTERVAL - elapsed)

            try:
                fallback = _blocks_to_fallback(blocks)
                await self.web_client.chat_postMessage(
                    channel=channel,
                    text=fallback,
                    blocks=blocks,
                    thread_ts=thread_ts,
                )
                self._last_post = time.monotonic()
            except Exception as e:
                # Handle rate limit (429)
                retry_after = getattr(getattr(e, "response", None), "headers", {}).get(
                    "Retry-After"
                )
                if retry_after:
                    await asyncio.sleep(int(retry_after))
                    try:
                        await self.web_client.chat_postMessage(
                            channel=channel,
                            text=fallback,
                            blocks=blocks,
                            thread_ts=thread_ts,
                        )
                        self._last_post = time.monotonic()
                    except Exception:
                        logger.exception("Failed to post Slack message (after retry)")
                else:
                    logger.exception("Failed to post Slack message")


# ── Block Kit helpers ────────────────────────────────────────


def _header_block(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text}}


def _section_block(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _error_blocks(message: str) -> list[dict]:
    return [
        _header_block("오류"),
        _section_block(f":warning: {message}"),
    ]


def _blocks_to_fallback(blocks: list[dict]) -> str:
    """Extract plain text from blocks for the fallback field."""
    parts = []
    for b in blocks:
        if b.get("type") == "header":
            parts.append(b.get("text", {}).get("text", ""))
        elif b.get("type") == "section":
            parts.append(b.get("text", {}).get("text", ""))
    return "\n".join(parts)[:200]


def _safe_json_loads(text: str, default: object) -> object:
    """Parse JSON string, returning default on failure."""
    try:
        return __import__("json").loads(text)
    except (ValueError, TypeError):
        return default
