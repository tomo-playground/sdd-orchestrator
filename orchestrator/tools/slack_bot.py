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
from orchestrator.tools.slack_templates import (
    agent_response_blocks,
    blocks_to_fallback,
    error_blocks,
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

    def register_active_thread(self, ts: str) -> None:
        """Register a message ts so thread replies are handled."""
        if ts and ts not in self._active_threads:
            self._active_threads.append(ts)

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
                error_blocks("권한 없음: 이 명령을 실행할 권한이 없습니다."),
                thread_ts,
            )
            return

        # Acknowledge receipt with eyes emoji
        await self._add_reaction(channel, ts, "eyes")

        # Delegate to Claude Agent
        success = True
        try:
            response = await asyncio.wait_for(
                self._ask_agent(text), timeout=SLACK_BOT_AGENT_TIMEOUT
            )
            blocks = agent_response_blocks(response)
        except TimeoutError:
            success = False
            logger.warning("Agent timeout for message: %s", text[:50])
            blocks = error_blocks("응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except Exception:
            success = False
            logger.exception("Agent call failed for message: %s", text[:50])
            blocks = error_blocks("명령 처리 중 오류가 발생했습니다.")

        await self._post_message(channel, blocks, thread_ts)

        # Replace eyes with result emoji
        await self._remove_reaction(channel, ts, "eyes")
        await self._add_reaction(channel, ts, "white_check_mark" if success else "x")

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

    # ── Public notification API ───────────────────────────────

    async def post_notification(self, text: str, blocks: list[dict] | None = None) -> str | None:
        """Send a notification to the configured channel. Returns ts or None."""
        if not self.web_client:
            logger.info("SlackBot not connected, logging only: %s", text[:200])
            return None

        resp = await self._rate_limited_post(SLACK_BOT_ALLOWED_CHANNEL, text, blocks)
        ts = resp.get("ts") if resp else None
        if ts:
            self.register_active_thread(ts)
        return ts

    # ── Emoji reactions ─────────────────────────────────────

    async def _add_reaction(self, channel: str, timestamp: str, emoji: str) -> None:
        """Add an emoji reaction to a message. Silently ignores errors."""
        if not self.web_client:
            return
        try:
            await self.web_client.reactions_add(channel=channel, timestamp=timestamp, name=emoji)
        except Exception:
            logger.debug("Failed to add reaction :%s: to %s", emoji, timestamp)

    async def _remove_reaction(self, channel: str, timestamp: str, emoji: str) -> None:
        """Remove an emoji reaction from a message. Silently ignores errors."""
        if not self.web_client:
            return
        try:
            await self.web_client.reactions_remove(channel=channel, timestamp=timestamp, name=emoji)
        except Exception:
            logger.debug("Failed to remove reaction :%s: from %s", emoji, timestamp)

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
        fallback = blocks_to_fallback(blocks)
        await self._rate_limited_post(channel, fallback, blocks, thread_ts)

    async def _rate_limited_post(
        self,
        channel: str,
        text: str,
        blocks: list[dict] | None = None,
        thread_ts: str | None = None,
    ) -> dict | None:
        """Post via chat_postMessage with rate-limit guard + single 429 retry."""
        async with self._post_lock:
            elapsed = time.monotonic() - self._last_post
            if elapsed < SLACK_BOT_CHAT_INTERVAL:
                await asyncio.sleep(SLACK_BOT_CHAT_INTERVAL - elapsed)

            try:
                resp = await self.web_client.chat_postMessage(
                    channel=channel,
                    text=text,
                    blocks=blocks,
                    thread_ts=thread_ts,
                )
                self._last_post = time.monotonic()
                return resp
            except Exception as e:
                retry_after = getattr(getattr(e, "response", None), "headers", {}).get(
                    "Retry-After"
                )
                if retry_after:
                    try:
                        delay = int(retry_after)
                    except (ValueError, TypeError):
                        delay = 1
                    await asyncio.sleep(delay)
                    try:
                        resp = await self.web_client.chat_postMessage(
                            channel=channel,
                            text=text,
                            blocks=blocks,
                            thread_ts=thread_ts,
                        )
                        self._last_post = time.monotonic()
                        return resp
                    except Exception:
                        logger.exception("Failed to post Slack message (after retry)")
                        return None
                logger.exception("Failed to post Slack message")
                return None
