"""Unit tests for Slack notification tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.tools.notify import (
    do_notify_human,
    init_notify,
    send_daily_report,
)
from orchestrator.tools.slack_bot import SlackBotListener


@pytest.fixture(autouse=True)
def _reset_bot():
    """Reset module-level _bot after each test."""
    yield
    init_notify(None)


def _make_bot(ts: str | None = "1234.5678") -> SlackBotListener:
    """Create a mock SlackBotListener with post_notification."""
    bot = MagicMock(spec=SlackBotListener)
    bot.post_notification = AsyncMock(return_value=ts)
    return bot


class TestNotifyHuman:
    @pytest.mark.asyncio
    async def test_sends_via_bot(self):
        bot = _make_bot("1234.5678")
        init_notify(bot)
        result = await do_notify_human({"message": "test", "level": "info"})

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["sent"] is True
        assert data["channel"] == "slack"
        assert data["ts"] == "1234.5678"
        bot.post_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_level_prefix_info(self):
        bot = _make_bot()
        init_notify(bot)
        await do_notify_human({"message": "test", "level": "info"})

        call_text = bot.post_notification.call_args[0][0]
        assert call_text.startswith("\u2139\ufe0f")

    @pytest.mark.asyncio
    async def test_level_prefix_warning(self):
        bot = _make_bot()
        init_notify(bot)
        await do_notify_human({"message": "test", "level": "warning"})

        call_text = bot.post_notification.call_args[0][0]
        assert call_text.startswith("\u26a0\ufe0f")

    @pytest.mark.asyncio
    async def test_level_prefix_critical(self):
        bot = _make_bot()
        init_notify(bot)
        await do_notify_human({"message": "test", "level": "critical"})

        call_text = bot.post_notification.call_args[0][0]
        assert call_text.startswith("\U0001f6a8")

    @pytest.mark.asyncio
    async def test_truncation(self):
        bot = _make_bot()
        init_notify(bot)
        long_message = "x" * 5000
        await do_notify_human({"message": long_message, "level": "info"})

        call_text = bot.post_notification.call_args[0][0]
        assert len(call_text) <= 4010
        assert "(truncated)" in call_text

    @pytest.mark.asyncio
    async def test_fallback_when_no_bot(self):
        """_bot=None → log_only fallback."""
        init_notify(None)
        result = await do_notify_human({"message": "test", "level": "info"})

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["sent"] is False
        assert data["channel"] == "log_only"

    @pytest.mark.asyncio
    async def test_fallback_when_bot_returns_none(self):
        """Bot returns None (disconnected) → log_only fallback."""
        bot = _make_bot(ts=None)
        init_notify(bot)
        result = await do_notify_human({"message": "test", "level": "info"})

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["sent"] is False
        assert data["channel"] == "log_only"

    @pytest.mark.asyncio
    async def test_kst_timestamp(self):
        """Timestamp should use KST, not UTC."""
        bot = _make_bot()
        init_notify(bot)
        await do_notify_human({"message": "test", "level": "info"})

        blocks = bot.post_notification.call_args[0][1]
        context = [b for b in blocks if b["type"] == "context"][0]
        assert "KST" in context["elements"][0]["text"]
        assert "UTC" not in context["elements"][0]["text"]


class TestNotifyWithLinks:
    @pytest.mark.asyncio
    async def test_with_links(self):
        """Links should produce an actions block with buttons."""
        bot = _make_bot()
        init_notify(bot)
        links = [
            {"text": "PR #176", "url": "https://github.com/test/pull/176"},
            {"text": "Actions", "url": "https://github.com/test/actions"},
        ]
        await do_notify_human({"message": "test", "level": "info", "links": links})

        blocks = bot.post_notification.call_args[0][1]
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 1
        assert len(actions[0]["elements"]) == 2
        assert actions[0]["elements"][0]["text"]["text"] == "PR #176"

    @pytest.mark.asyncio
    async def test_without_links(self):
        """No links → no actions block."""
        bot = _make_bot()
        init_notify(bot)
        await do_notify_human({"message": "test", "level": "info"})

        blocks = bot.post_notification.call_args[0][1]
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_links_max_5(self):
        """More than 5 links → only first 5 rendered."""
        bot = _make_bot()
        init_notify(bot)
        links = [{"text": f"Link {i}", "url": f"https://example.com/{i}"} for i in range(8)]
        await do_notify_human({"message": "test", "level": "info", "links": links})

        blocks = bot.post_notification.call_args[0][1]
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions[0]["elements"]) == 5


class TestBuildLinkButtons:
    def test_empty_links(self):
        from orchestrator.tools.slack_templates import link_buttons

        assert link_buttons([]) is None

    def test_single_link(self):
        from orchestrator.tools.slack_templates import link_buttons

        result = link_buttons([{"text": "PR", "url": "https://example.com"}])
        assert result["type"] == "actions"
        assert len(result["elements"]) == 1

    def test_max_5_links(self):
        from orchestrator.tools.slack_templates import link_buttons

        links = [{"text": f"L{i}", "url": f"https://example.com/{i}"} for i in range(8)]
        result = link_buttons(links)
        assert len(result["elements"]) == 5


_CLI_RETURN = {"content": [{"type": "text", "text": '{"sent": true, "channel": "slack"}'}]}


class TestCliEntrypoint:
    @pytest.mark.asyncio
    async def test_cli_parses_args(self):
        """CLI should parse message, level, and links."""
        with (
            patch("sys.argv", ["notify", "테스트 메시지", "--level", "warning"]),
            patch(
                "orchestrator.tools.notify.do_notify_human",
                new_callable=AsyncMock,
                return_value=_CLI_RETURN,
            ) as mock_notify,
        ):
            from orchestrator.tools.notify import _cli_main

            await _cli_main()
            mock_notify.assert_called_once()
            args = mock_notify.call_args[0][0]
            assert args["message"] == "테스트 메시지"
            assert args["level"] == "warning"
            assert args["links"] == []

    @pytest.mark.asyncio
    async def test_cli_with_links(self):
        """CLI --link flag should produce links list."""
        with (
            patch(
                "sys.argv",
                ["notify", "msg", "--link", "PR", "https://example.com"],
            ),
            patch(
                "orchestrator.tools.notify.do_notify_human",
                new_callable=AsyncMock,
                return_value=_CLI_RETURN,
            ) as mock_notify,
        ):
            from orchestrator.tools.notify import _cli_main

            await _cli_main()
            args = mock_notify.call_args[0][0]
            assert args["links"] == [{"text": "PR", "url": "https://example.com"}]


class TestSendDailyReport:
    @pytest.mark.asyncio
    async def test_sends_via_bot(self):
        bot = _make_bot("9999.1111")
        init_notify(bot)
        summary = {
            "completed_prs": ["#65 (SP-067)"],
            "in_progress": ["SP-069 (running)"],
            "blockers": [],
            "sentry_issues": {"open": 2, "autofix_prs": 1},
        }
        result = await send_daily_report(summary)

        assert result is True
        call_text = bot.post_notification.call_args[0][0]
        assert "Coding Machine Report" in call_text
        blocks = bot.post_notification.call_args[0][1]
        block_text = json.dumps(blocks)
        assert "#65" in block_text
        assert "SP-069" in block_text

    @pytest.mark.asyncio
    async def test_no_bot_returns_false(self):
        init_notify(None)
        result = await send_daily_report({"completed_prs": [], "in_progress": [], "blockers": []})
        assert result is False
