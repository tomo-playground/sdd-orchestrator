"""Unit tests for Slack Bot listener — Claude Agent dispatch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import orchestrator.tools.slack_bot as _slack_bot_module
from orchestrator.tools.slack_bot import (
    SlackBotListener,
    pause_orchestrator,
    resume_orchestrator,
    set_daemon,
)

# ── Fixture ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_daemon():
    """Restore global _daemon state after each test."""
    prev = _slack_bot_module._daemon
    yield
    _slack_bot_module._daemon = prev


@pytest.fixture()
def daemon():
    """Create a mock daemon with pause_event."""
    d = MagicMock()
    d.pause_event = asyncio.Event()
    return d


@pytest.fixture()
def mcp_server():
    """Create a mock MCP server."""
    return MagicMock()


@pytest.fixture()
def bot(mcp_server):
    """Create a SlackBotListener with mock mcp_server."""
    return SlackBotListener(mcp_server=mcp_server)


# ── DoD 1: Socket Mode lifecycle ─────────────────────────────


class TestSlackBotNoTokens:
    """Test that bot does not start without tokens."""

    @pytest.mark.asyncio
    async def test_no_tokens_skips_start(self):
        """main.py should skip bot init when tokens are empty."""
        with (
            patch("orchestrator.config.SLACK_BOT_TOKEN", ""),
            patch("orchestrator.config.SLACK_APP_TOKEN", ""),
        ):
            from orchestrator.main import OrchestratorDaemon

            daemon = OrchestratorDaemon.__new__(OrchestratorDaemon)
            daemon.slack_bot = None
            await daemon._maybe_start_slack_bot()
            assert daemon.slack_bot is None


# ── Agent delegation ──────────────────────────────────────────


_PATCH_ALLOW_CHANNEL = "orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_CHANNEL"
_PATCH_ALLOW_USERS = "orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_USERS"


class TestSlackBotMention:
    @pytest.mark.asyncio
    async def test_handle_mention_calls_agent(self, bot):
        """app_mention event triggers Claude Agent call."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock()

        event = {
            "text": "<@U12345> 현재 상태 알려줘",
            "channel": "C001",
            "user": "U001",
            "ts": "1234.5678",
        }
        say = AsyncMock()

        with (
            patch(_PATCH_ALLOW_CHANNEL, ""),
            patch(_PATCH_ALLOW_USERS, ""),
            patch.object(bot, "_ask_agent", new_callable=AsyncMock) as mock_agent,
        ):
            mock_agent.return_value = "현재 실행 중인 태스크가 2개 있습니다."
            await bot._handle_mention(event, say)
            mock_agent.assert_called_once_with("현재 상태 알려줘")

    @pytest.mark.asyncio
    async def test_ignore_bot_message(self, bot):
        """Events with bot_id should be silently ignored."""
        event = {"text": "상태", "channel": "C001", "ts": "1234.5678", "bot_id": "B123"}
        say = AsyncMock()

        with patch.object(bot, "_ask_agent", new_callable=AsyncMock) as mock_agent:
            await bot._handle_mention(event, say)
            mock_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_timeout_returns_error(self, bot):
        """Agent timeout should return user-friendly error."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock()

        event = {"text": "<@U12345> 복잡한 질문", "channel": "C001", "user": "U001", "ts": "1.0"}

        async def slow_agent(_text):
            await asyncio.sleep(10)

        with (
            patch(_PATCH_ALLOW_CHANNEL, ""),
            patch(_PATCH_ALLOW_USERS, ""),
            patch.object(bot, "_ask_agent", side_effect=slow_agent),
            patch("orchestrator.tools.slack_bot.SLACK_BOT_AGENT_TIMEOUT", 0.01),
        ):
            await bot._handle_mention(event, AsyncMock())

        # Should have posted an error message
        bot.web_client.chat_postMessage.assert_called_once()
        blocks = bot.web_client.chat_postMessage.call_args.kwargs.get(
            "blocks", bot.web_client.chat_postMessage.call_args[1].get("blocks", [])
        )
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        assert any("시간" in t for t in texts)

    @pytest.mark.asyncio
    async def test_agent_exception_returns_error(self, bot):
        """Agent exception should return user-friendly error."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock()

        event = {"text": "<@U12345> 테스트", "channel": "C001", "user": "U001", "ts": "1.0"}

        with (
            patch(_PATCH_ALLOW_CHANNEL, ""),
            patch(_PATCH_ALLOW_USERS, ""),
            patch.object(
                bot, "_ask_agent", new_callable=AsyncMock, side_effect=RuntimeError("fail")
            ),
        ):
            await bot._handle_mention(event, AsyncMock())

        bot.web_client.chat_postMessage.assert_called_once()
        blocks = bot.web_client.chat_postMessage.call_args.kwargs.get(
            "blocks", bot.web_client.chat_postMessage.call_args[1].get("blocks", [])
        )
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        assert any("오류" in t for t in texts)


class TestSlackBotRestart:
    @pytest.mark.asyncio
    async def test_restart_on_crash(self):
        """Restart wrapper should retry after crash."""
        from orchestrator.main import OrchestratorDaemon

        daemon = OrchestratorDaemon.__new__(OrchestratorDaemon)
        daemon.stop_event = asyncio.Event()
        daemon.slack_bot = MagicMock()

        call_count = 0

        async def crash_start():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Socket failed")
            # Third time succeeds but stop_event set
            daemon.stop_event.set()

        daemon.slack_bot.start = crash_start
        daemon.slack_bot.stop = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await daemon._run_slack_bot_with_restart()

        assert call_count == 3


# ── Permission checks ────────────────────────────────────────


class TestPermissionCheck:
    @pytest.mark.asyncio
    async def test_denied_channel_silently_ignored(self, bot):
        """Events in non-allowed channels should be silently ignored."""
        event = {"text": "<@U12345> 상태", "channel": "C_OTHER", "ts": "1.0", "user": "U001"}
        with (
            patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_CHANNEL", "C_ALLOWED"),
            patch.object(bot, "_ask_agent", new_callable=AsyncMock) as mock_agent,
            patch.object(bot, "_post_message", new_callable=AsyncMock) as mock_post,
        ):
            await bot._handle_mention(event, AsyncMock())
        mock_agent.assert_not_called()
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_denied_user_gets_error_message(self, bot):
        """Non-allowed users should receive a permission denied message."""
        event = {
            "text": "<@U12345> 머지 #177",
            "channel": "C001",
            "ts": "1.0",
            "user": "U_STRANGER",
        }
        with (
            patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_CHANNEL", ""),
            patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_USERS", "U_ADMIN"),
            patch.object(bot, "_ask_agent", new_callable=AsyncMock) as mock_agent,
            patch.object(bot, "_post_message", new_callable=AsyncMock) as mock_post,
        ):
            await bot._handle_mention(event, AsyncMock())
        mock_agent.assert_not_called()
        mock_post.assert_called_once()
        blocks = mock_post.call_args[0][1]
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        assert any("권한" in t for t in texts)

    def test_is_allowed_channel_empty_allows_all(self, bot):
        with patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_CHANNEL", ""):
            assert bot._is_allowed_channel("ANY_CHANNEL") is True

    def test_is_allowed_user_empty_allows_all(self, bot):
        with patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_USERS", ""):
            assert bot._is_allowed_user("ANY_USER") is True


# ── Emoji reactions ──────────────────────────────────────────


class TestEmojiReactions:
    @pytest.mark.asyncio
    async def test_success_adds_eyes_then_check(self, bot):
        """Successful agent call: eyes → remove eyes → white_check_mark."""
        bot.web_client = AsyncMock()
        event = {
            "text": "<@U12345> 상태",
            "channel": "C001",
            "user": "U001",
            "ts": "1.0",
        }

        with (
            patch(_PATCH_ALLOW_CHANNEL, ""),
            patch(_PATCH_ALLOW_USERS, ""),
            patch.object(bot, "_ask_agent", new_callable=AsyncMock, return_value="OK"),
        ):
            await bot._handle_mention(event, AsyncMock())

        reaction_calls = bot.web_client.reactions_add.call_args_list
        emoji_names = [c.kwargs["name"] for c in reaction_calls]
        assert "eyes" in emoji_names
        assert "white_check_mark" in emoji_names

        remove_calls = bot.web_client.reactions_remove.call_args_list
        removed = [c.kwargs["name"] for c in remove_calls]
        assert "eyes" in removed

    @pytest.mark.asyncio
    async def test_failure_adds_x_emoji(self, bot):
        """Failed agent call: eyes → remove eyes → x."""
        bot.web_client = AsyncMock()
        event = {
            "text": "<@U12345> 실패",
            "channel": "C001",
            "user": "U001",
            "ts": "2.0",
        }

        with (
            patch(_PATCH_ALLOW_CHANNEL, ""),
            patch(_PATCH_ALLOW_USERS, ""),
            patch.object(
                bot, "_ask_agent", new_callable=AsyncMock, side_effect=RuntimeError("boom")
            ),
        ):
            await bot._handle_mention(event, AsyncMock())

        reaction_calls = bot.web_client.reactions_add.call_args_list
        emoji_names = [c.kwargs["name"] for c in reaction_calls]
        assert "x" in emoji_names

    @pytest.mark.asyncio
    async def test_reaction_failure_does_not_block(self, bot):
        """Reaction API failure should not prevent message posting."""
        bot.web_client = AsyncMock()
        bot.web_client.reactions_add.side_effect = Exception("API error")
        bot.web_client.reactions_remove.side_effect = Exception("API error")

        event = {
            "text": "<@U12345> 테스트",
            "channel": "C001",
            "user": "U001",
            "ts": "3.0",
        }

        with (
            patch(_PATCH_ALLOW_CHANNEL, ""),
            patch(_PATCH_ALLOW_USERS, ""),
            patch.object(bot, "_ask_agent", new_callable=AsyncMock, return_value="응답"),
        ):
            await bot._handle_mention(event, AsyncMock())

        # Message should still be posted despite reaction failures
        bot.web_client.chat_postMessage.assert_called_once()


# ── MCP tools: pause / resume ────────────────────────────────


class TestPauseResumeTool:
    @pytest.mark.asyncio
    async def test_pause_sets_event(self, daemon):
        """pause_orchestrator tool should set pause_event."""
        set_daemon(daemon)
        result = await pause_orchestrator.handler({})
        assert daemon.pause_event.is_set()
        assert not result.get("isError")

    @pytest.mark.asyncio
    async def test_resume_clears_event(self, daemon):
        """resume_orchestrator tool should clear pause_event."""
        set_daemon(daemon)
        daemon.pause_event.set()
        result = await resume_orchestrator.handler({})
        assert not daemon.pause_event.is_set()
        assert not result.get("isError")

    @pytest.mark.asyncio
    async def test_pause_no_daemon_returns_error(self):
        """pause with no daemon should return error."""
        set_daemon(None)
        result = await pause_orchestrator.handler({})
        assert result.get("isError")

    @pytest.mark.asyncio
    async def test_resume_no_daemon_returns_error(self):
        """resume with no daemon should return error."""
        set_daemon(None)
        result = await resume_orchestrator.handler({})
        assert result.get("isError")


# ── Thread message handler ────────────────────────────────────


class TestHandleThreadMessage:
    """Unit tests for _handle_thread_message — 6 branches."""

    @pytest.mark.asyncio
    async def test_no_thread_ts_is_ignored(self, bot):
        """Channel-level messages (no thread_ts) are silently skipped."""
        event = {"text": "hello", "ts": "1.0"}
        say = AsyncMock()
        with patch.object(bot, "_handle_mention", new_callable=AsyncMock) as mock_mention:
            await bot._handle_thread_message(event, say)
        mock_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_subtype_event_is_ignored(self, bot):
        """Events with subtype (e.g. message_changed) are silently skipped."""
        event = {"text": "hello", "ts": "1.0", "thread_ts": "1.0", "subtype": "message_changed"}
        say = AsyncMock()
        with patch.object(bot, "_handle_mention", new_callable=AsyncMock) as mock_mention:
            await bot._handle_thread_message(event, say)
        mock_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_message_is_ignored(self, bot):
        """Messages with bot_id are silently skipped."""
        event = {"text": "hello", "ts": "1.0", "thread_ts": "1.0", "bot_id": "B123"}
        say = AsyncMock()
        with patch.object(bot, "_handle_mention", new_callable=AsyncMock) as mock_mention:
            await bot._handle_thread_message(event, say)
        mock_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_mention_no_active_thread_is_ignored(self, bot):
        """No @mention and not an active thread — silently skipped."""
        bot._bot_user_id = "U_BOT"
        event = {"text": "no mention here", "ts": "1.0", "thread_ts": "T_INACTIVE"}
        say = AsyncMock()
        with patch.object(bot, "_handle_mention", new_callable=AsyncMock) as mock_mention:
            await bot._handle_thread_message(event, say)
        mock_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_explicit_mention_triggers_response(self, bot):
        """Explicit @mention in thread triggers _handle_mention."""
        bot._bot_user_id = "U_BOT"
        event = {"text": "<@U_BOT> 현재 상태", "ts": "2.0", "thread_ts": "1.0"}
        say = AsyncMock()
        with patch.object(bot, "_handle_mention", new_callable=AsyncMock) as mock_mention:
            await bot._handle_thread_message(event, say)
        mock_mention.assert_called_once_with(event, say)

    @pytest.mark.asyncio
    async def test_active_thread_triggers_response(self, bot):
        """Message in an active thread (no @mention) triggers _handle_mention."""
        bot._bot_user_id = "U_BOT"
        bot._active_threads.append("T_ACTIVE")
        event = {"text": "후속 질문", "ts": "3.0", "thread_ts": "T_ACTIVE"}
        say = AsyncMock()
        with patch.object(bot, "_handle_mention", new_callable=AsyncMock) as mock_mention:
            await bot._handle_thread_message(event, say)
        mock_mention.assert_called_once_with(event, say)


# ── post_notification ────────────────────────────────────────


_PATCH_CHANNEL = "orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_CHANNEL"
_PATCH_CHAT_INTERVAL = "orchestrator.tools.slack_bot.SLACK_BOT_CHAT_INTERVAL"


class TestPostNotification:
    @pytest.mark.asyncio
    async def test_returns_ts_and_registers_thread(self, bot):
        """Successful post returns ts and auto-registers active thread."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock(return_value={"ts": "111.222"})

        with (
            patch(_PATCH_CHANNEL, "C001"),
            patch(_PATCH_CHAT_INTERVAL, 0),
        ):
            ts = await bot.post_notification("hello", [{"type": "section"}])

        assert ts == "111.222"
        assert "111.222" in bot._active_threads

    @pytest.mark.asyncio
    async def test_no_web_client_returns_none(self, bot):
        """When web_client is None, returns None (fallback)."""
        bot.web_client = None
        ts = await bot.post_notification("hello")
        assert ts is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self, bot):
        """Exception during post returns None."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock(side_effect=RuntimeError("fail"))

        with (
            patch(_PATCH_CHANNEL, "C001"),
            patch(_PATCH_CHAT_INTERVAL, 0),
        ):
            ts = await bot.post_notification("hello")

        assert ts is None

    @pytest.mark.asyncio
    async def test_rate_limit_retry_succeeds(self, bot):
        """429 with Retry-After header retries and succeeds."""
        bot.web_client = AsyncMock()

        err = Exception("rate_limited")
        err.response = MagicMock()
        err.response.headers = {"Retry-After": "1"}
        bot.web_client.chat_postMessage = AsyncMock(side_effect=[err, {"ts": "333.444"}])

        with (
            patch(_PATCH_CHANNEL, "C001"),
            patch(_PATCH_CHAT_INTERVAL, 0),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            ts = await bot.post_notification("hello")

        assert ts == "333.444"
        assert "333.444" in bot._active_threads

    @pytest.mark.asyncio
    async def test_rate_limit_retry_also_fails(self, bot):
        """429 retry also fails → returns None."""
        bot.web_client = AsyncMock()

        err = Exception("rate_limited")
        err.response = MagicMock()
        err.response.headers = {"Retry-After": "1"}
        bot.web_client.chat_postMessage = AsyncMock(side_effect=[err, RuntimeError("also_fail")])

        with (
            patch(_PATCH_CHANNEL, "C001"),
            patch(_PATCH_CHAT_INTERVAL, 0),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            ts = await bot.post_notification("hello")

        assert ts is None

    @pytest.mark.asyncio
    async def test_posts_to_configured_channel(self, bot):
        """Message should be posted to SLACK_BOT_ALLOWED_CHANNEL."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock(return_value={"ts": "1.0"})

        with (
            patch(_PATCH_CHANNEL, "C_CONFIGURED"),
            patch(_PATCH_CHAT_INTERVAL, 0),
        ):
            await bot.post_notification("test", [{"type": "section"}])

        call_kwargs = bot.web_client.chat_postMessage.call_args.kwargs
        assert call_kwargs["channel"] == "C_CONFIGURED"
        assert call_kwargs["text"] == "test"
        assert call_kwargs["blocks"] == [{"type": "section"}]


# ── Block Kit helpers ─────────────────────────────────────────


class TestBlockKit:
    def test_text_to_blocks_normal(self):
        """Normal text should produce a single section block."""
        from orchestrator.tools.slack_templates import agent_response_blocks

        blocks = agent_response_blocks("Hello world")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "section"
        assert blocks[0]["text"]["text"] == "Hello world"

    def test_text_to_blocks_truncation(self):
        """Text > 2900 chars should be truncated with ellipsis."""
        from orchestrator.tools.slack_templates import agent_response_blocks

        long_text = "x" * 3500
        blocks = agent_response_blocks(long_text)
        text = blocks[0]["text"]["text"]
        assert len(text) <= 3000
        assert text.endswith("\u2026")

    def test_error_blocks_structure(self):
        """Error blocks should have header + section."""
        from orchestrator.tools.slack_templates import error_blocks

        blocks = error_blocks("test error")
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "section"
        assert "test error" in blocks[1]["text"]["text"]
