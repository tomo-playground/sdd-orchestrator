"""Unit tests for Slack Bot listener and command dispatch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.tools.slack_bot import SlackBotListener, _header_block

# ── Fixture ──────────────────────────────────────────────────


@pytest.fixture()
def daemon():
    """Create a mock daemon with pause_event."""
    d = MagicMock()
    d.pause_event = asyncio.Event()
    return d


@pytest.fixture()
def bot(daemon):
    """Create a SlackBotListener with mock daemon."""
    return SlackBotListener(daemon=daemon)


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


class TestSlackBotMention:
    @pytest.mark.asyncio
    async def test_handle_mention_calls_dispatch(self, bot):
        """app_mention event triggers command dispatch."""
        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock()

        event = {"text": "<@U12345> 상태", "channel": "C001", "ts": "1234.5678"}
        say = AsyncMock()

        with patch.object(bot, "_cmd_status", new_callable=AsyncMock) as mock_status:
            mock_status.return_value = [_header_block("test")]
            await bot._handle_mention(event, say)
            mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_ignore_bot_message(self, bot):
        """Events with bot_id should be silently ignored."""
        event = {"text": "상태", "channel": "C001", "ts": "1234.5678", "bot_id": "B123"}
        say = AsyncMock()

        with patch.object(bot, "_dispatch_command") as mock_dispatch:
            await bot._handle_mention(event, say)
            mock_dispatch.assert_not_called()


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


# ── DoD 2: Command dispatch ──────────────────────────────────


class TestCommandParsing:
    def test_parse_cmd_key_status(self, bot):
        assert bot._parse_cmd_key("상태") == "상태"

    def test_parse_cmd_key_launch(self, bot):
        assert bot._parse_cmd_key("실행 SP-077") == "실행"

    def test_parse_cmd_key_merge(self, bot):
        assert bot._parse_cmd_key("머지 #177") == "머지"

    def test_parse_cmd_key_pause(self, bot):
        assert bot._parse_cmd_key("중지") == "중지"

    def test_parse_cmd_key_resume(self, bot):
        assert bot._parse_cmd_key("시작") == "시작"

    def test_parse_cmd_key_backlog(self, bot):
        assert bot._parse_cmd_key("백로그") == "백로그"

    def test_parse_cmd_key_unknown(self, bot):
        assert bot._parse_cmd_key("뭐야 이건") == "help"


class TestCmdLaunch:
    @pytest.mark.asyncio
    async def test_launch_calls_do_launch(self, bot):
        """'실행 SP-077' should call do_launch_sdd_run with SP-077."""
        with patch(
            "orchestrator.tools.worktree.do_launch_sdd_run",
            new_callable=AsyncMock,
            return_value={"content": [{"type": "text", "text": "Launched SP-077"}]},
        ) as mock_launch:
            blocks = await bot._cmd_launch("실행 SP-077")
            mock_launch.assert_called_once_with("SP-077")

        # Should have success blocks (not error)
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        assert any("SP-077" in t for t in texts)

    @pytest.mark.asyncio
    async def test_launch_invalid_no_sp(self, bot):
        """'실행' without SP-NNN should return error."""
        blocks = await bot._cmd_launch("실행")
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        assert any("태스크 ID" in t for t in texts)


class TestCmdMerge:
    @pytest.mark.asyncio
    async def test_merge_calls_do_merge(self, bot):
        with patch(
            "orchestrator.tools.github.do_merge_pr",
            new_callable=AsyncMock,
            return_value={"content": [{"type": "text", "text": "Merged PR #177"}]},
        ) as mock_merge:
            await bot._cmd_merge("머지 #177")
            mock_merge.assert_called_once_with(177)


class TestCmdPause:
    def test_pause_uses_pause_event(self, bot, daemon):
        """'중지' should set pause_event, not stop_event."""
        bot._cmd_pause()
        assert daemon.pause_event.is_set()

    def test_resume_clears_pause_event(self, bot, daemon):
        daemon.pause_event.set()
        bot._cmd_resume()
        assert not daemon.pause_event.is_set()


class TestCmdBacklog:
    @pytest.mark.asyncio
    async def test_backlog_returns_top5(self, bot):
        from orchestrator.tools.backlog import BacklogTask

        tasks = [
            BacklogTask(id=f"SP-{i:03d}", priority="P0", description=f"Task {i}") for i in range(10)
        ]
        with patch("orchestrator.tools.backlog.parse_backlog", return_value=tasks):
            blocks = await bot._cmd_backlog()

        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        full_text = "\n".join(texts)
        assert "SP-004" in full_text
        # SP-005 through SP-009 should NOT be shown (only top 5)
        assert "SP-005" not in full_text


class TestCmdUnknown:
    def test_help_shows_available_commands(self, bot):
        blocks = bot._cmd_help()
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        full_text = "\n".join(texts)
        assert "상태" in full_text
        assert "실행" in full_text
        assert "머지" in full_text


class TestCmdStatus:
    @pytest.mark.asyncio
    async def test_status_gathers_data(self, bot):
        """Status command should call backlog, gh, and worktree."""
        from orchestrator.tools.backlog import BacklogTask

        tasks = [
            BacklogTask(
                id="SP-077",
                priority="P0",
                description="Test",
                spec_status="running",
            )
        ]

        with (
            patch("orchestrator.tools.backlog.parse_backlog", return_value=tasks),
            patch(
                "orchestrator.tools.github._run_gh_command",
                new_callable=AsyncMock,
                return_value={"data": []},
            ),
            patch(
                "orchestrator.tools.worktree.do_check_running_worktrees",
                new_callable=AsyncMock,
                return_value={"content": [{"type": "text", "text": "[]"}]},
            ),
        ):
            blocks = await bot._cmd_status()

        assert len(blocks) >= 3


# ── DoD 2: Concurrent write serialization ────────────────────


class TestPermissionCheck:
    @pytest.mark.asyncio
    async def test_denied_channel_silently_ignored(self, bot):
        """Events in non-allowed channels should be silently ignored."""
        event = {"text": "<@U12345> 상태", "channel": "C_OTHER", "ts": "1.0", "user": "U001"}
        with (
            patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_CHANNEL", "C_ALLOWED"),
            patch.object(bot, "_dispatch_command") as mock_dispatch,
            patch.object(bot, "_post_message", new_callable=AsyncMock) as mock_post,
        ):
            await bot._handle_mention(event, AsyncMock())
        mock_dispatch.assert_not_called()
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
            patch("orchestrator.tools.slack_bot.SLACK_BOT_ALLOWED_USERS", "U_ADMIN"),
            patch.object(bot, "_dispatch_command") as mock_dispatch,
            patch.object(bot, "_post_message", new_callable=AsyncMock) as mock_post,
        ):
            await bot._handle_mention(event, AsyncMock())
        mock_dispatch.assert_not_called()
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


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_write_serialized(self, bot):
        """Write commands (실행) should be serialized via _cmd_lock."""
        execution_order = []

        async def slow_launch(text):
            execution_order.append("start")
            await asyncio.sleep(0.05)
            execution_order.append("end")
            return [_header_block("done")]

        bot.web_client = AsyncMock()
        bot.web_client.chat_postMessage = AsyncMock()

        with patch.object(bot, "_cmd_launch", side_effect=slow_launch):
            event1 = {"text": "<@U1> 실행 SP-001", "channel": "C001", "ts": "1.0"}
            event2 = {"text": "<@U1> 실행 SP-002", "channel": "C001", "ts": "2.0"}

            await asyncio.gather(
                bot._handle_mention(event1, AsyncMock()),
                bot._handle_mention(event2, AsyncMock()),
            )

        # Both should complete — serialized means start-end-start-end
        assert execution_order == ["start", "end", "start", "end"]
