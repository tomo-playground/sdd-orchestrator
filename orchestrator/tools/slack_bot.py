"""Slack Bot listener — Socket Mode event handling + Claude Agent dispatch."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from typing import TYPE_CHECKING

from claude_agent_sdk import tool

from orchestrator.config import (
    SLACK_BOT_AGENT_TIMEOUT,
    SLACK_BOT_ALLOWED_CHANNEL,
    SLACK_BOT_ALLOWED_USERS,
    SLACK_BOT_CHAT_INTERVAL,
    SLACK_BOT_TOKEN,
)

if TYPE_CHECKING:
    from slack_bolt.async_app import AsyncApp
    from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)

# ── Module-level daemon reference for MCP tools ───────────

_daemon = None


def set_daemon(daemon: object) -> None:
    """Store daemon reference for pause/resume MCP tools."""
    global _daemon  # noqa: PLW0603
    _daemon = daemon


def _ok(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}]}


def _tool_error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "isError": True}


# ── MCP Tools: pause/resume ──────────────────────────────


@tool("pause_orchestrator", "Pause the orchestrator cycle loop", {})
async def pause_orchestrator(args: dict) -> dict:
    """Pause the orchestrator daemon cycle."""
    if _daemon and hasattr(_daemon, "pause_event"):
        _daemon.pause_event.set()
        return _ok("오케스트레이터를 일시정지했습니다.")
    return _tool_error("Daemon not available")


@tool("resume_orchestrator", "Resume the orchestrator cycle loop", {})
async def resume_orchestrator(args: dict) -> dict:
    """Resume the orchestrator daemon cycle."""
    if _daemon and hasattr(_daemon, "pause_event"):
        _daemon.pause_event.clear()
        return _ok("오케스트레이터를 재개했습니다.")
    return _tool_error("Daemon not available")


# ── Slack Bot Listener ────────────────────────────────────


class SlackBotListener:
    """Socket Mode listener that receives Slack mentions and delegates to Claude Agent."""

    def __init__(self, mcp_server: object) -> None:
        self._mcp_server = mcp_server
        self._post_lock = asyncio.Lock()
        self._last_post: float = 0
        self._bot_user_id: str | None = None
        self._processed_ts: deque[str] = deque(maxlen=200)
        self._active_threads: deque[str] = deque(maxlen=200)
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
        self.app.event("message")(self._handle_thread_message)
        self.web_client = self.app.client
        self.web_client.timeout = SLACK_BOT_API_TIMEOUT

        try:
            resp = await self.web_client.auth_test()
            bot_user_id = resp.get("user_id")
            if bot_user_id:
                self._bot_user_id = bot_user_id
            else:
                logger.error("auth_test 응답에 user_id가 없습니다 — 스레드 멘션 응답 비활성화")
        except Exception as e:
            logger.exception("bot user_id 조회 실패 — 스레드 멘션 응답 비활성화: %s", e)

        self.handler = AsyncSocketModeHandler(self.app, SLACK_APP_TOKEN)
        await self.handler.connect_async()
        logger.info("SlackBot connected via Socket Mode")

    async def stop(self) -> None:
        """Disconnect gracefully."""
        if self.handler:
            await self.handler.disconnect_async()
            logger.info("SlackBot disconnected")

    # ── Event handlers ───────────────────────────────────────

    async def _handle_thread_message(self, event: dict, say) -> None:
        """Handle thread messages — respond if bot was mentioned OR thread is active."""
        # Only thread replies (not channel-level messages — those go through app_mention)
        thread_ts = event.get("thread_ts")
        if not thread_ts or event.get("subtype"):
            return
        if event.get("bot_id"):
            return

        # Respond if: explicit @mention OR bot already participated in this thread
        has_mention = self._bot_user_id and f"<@{self._bot_user_id}>" in event.get("text", "")
        is_active_thread = thread_ts in self._active_threads

        if not has_mention and not is_active_thread:
            return
        await self._handle_mention(event, say)

    async def _handle_mention(self, event: dict, say) -> None:
        """Handle app_mention events by delegating to Claude Agent."""
        if event.get("bot_id"):
            return

        # Dedup: app_mention + message events can both fire for thread mentions
        ts = event.get("ts", "")
        if ts in self._processed_ts:
            return
        self._processed_ts.append(ts)

        channel = event.get("channel", "")
        user_id = event.get("user", "")
        thread_ts = event.get("thread_ts") or event.get("ts", "")
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

        # Delegate to Claude Agent
        try:
            response = await asyncio.wait_for(
                self._ask_agent(text), timeout=SLACK_BOT_AGENT_TIMEOUT
            )
            blocks = _text_to_blocks(response)
        except TimeoutError:
            logger.warning("Agent timeout for message: %s", text[:50])
            blocks = _error_blocks("응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except Exception:
            logger.exception("Agent call failed for message: %s", text[:50])
            blocks = _error_blocks("명령 처리 중 오류가 발생했습니다.")

        await self._post_message(channel, blocks, thread_ts)

        # Track this thread as active so follow-up messages don't need @mention
        if thread_ts and thread_ts not in self._active_threads:
            self._active_threads.append(thread_ts)

    async def _ask_agent(self, text: str) -> str:
        """Query Claude Agent with the user's message."""
        from orchestrator.agents import create_slack_bot_options
        from orchestrator.utils import query_agent

        options = create_slack_bot_options(self._mcp_server)
        return await query_agent(options, text)

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


def _text_to_blocks(text: str) -> list[dict]:
    """Convert Agent text response to Block Kit blocks.

    Splits on double newlines into multiple section blocks with dividers
    for better readability. Each section is capped at 3000 chars (Slack limit).
    """
    max_block_text = 3000
    sections = [s.strip() for s in text.split("\n\n") if s.strip()]

    if not sections:
        return [_section_block("(빈 응답)")]

    blocks: list[dict] = []
    total_chars = 0
    char_limit = 2900

    for i, section in enumerate(sections):
        if total_chars + len(section) > char_limit:
            remaining = char_limit - total_chars
            if remaining > 50:
                blocks.append(_section_block(section[:remaining] + "…"))
            break
        if i > 0:
            blocks.append({"type": "divider"})
        blocks.append(_section_block(section[:max_block_text]))
        total_chars += len(section)

    return blocks


def _blocks_to_fallback(blocks: list[dict]) -> str:
    """Extract plain text from blocks for the fallback field."""
    parts = []
    for b in blocks:
        if b.get("type") == "header":
            parts.append(b.get("text", {}).get("text", ""))
        elif b.get("type") == "section":
            parts.append(b.get("text", {}).get("text", ""))
    return "\n".join(parts)[:200]
