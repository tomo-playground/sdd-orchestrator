"""Unit tests for Slack Bot listener — Claude Agent dispatch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import orchestrator.tools.slack_bot as _slack_bot_module
from orchestrator.tools.slack_bot import (
    SlackBotListener,
    _error_blocks,
    _text_to_blocks,
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


# ── Block Kit helpers ─────────────────────────────────────────


class TestBlockKit:
    def test_text_to_blocks_normal(self):
        """Normal text should produce a single section block."""
        blocks = _text_to_blocks("Hello world")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "section"
        assert blocks[0]["text"]["text"] == "Hello world"

    def test_text_to_blocks_truncation(self):
        """Text > 2900 chars should be truncated within Slack mrkdwn 3000-char limit."""
        long_text = "x" * 3500
        blocks = _text_to_blocks(long_text)
        text = blocks[0]["text"]["text"]
        assert len(text) <= 3000
        assert text.endswith("(응답이 잘렸습니다)")

    def test_error_blocks_structure(self):
        """Error blocks should have header + section."""
        blocks = _error_blocks("test error")
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "section"
        assert "test error" in blocks[1]["text"]["text"]
