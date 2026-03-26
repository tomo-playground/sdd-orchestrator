"""Unit tests for Slack notification tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from orchestrator.tools.notify import (
    _send_slack_message,
    do_notify_human,
    send_daily_report,
)

_PATCH_BOT_TOKEN = "orchestrator.config.SLACK_BOT_TOKEN"
_PATCH_BOT_CHANNEL = "orchestrator.config.SLACK_BOT_ALLOWED_CHANNEL"


class TestSendSlackMessage:
    @pytest.mark.asyncio
    async def test_bot_api_success(self):
        response = httpx.Response(200, json={"ok": True})
        mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
        mock_client_instance.post.return_value = response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(_PATCH_BOT_TOKEN, "xoxb-test-token"),
            patch(_PATCH_BOT_CHANNEL, "C001"),
            patch("orchestrator.tools.notify.httpx.AsyncClient", return_value=mock_client_instance),
            patch("orchestrator.tools.notify._last_slack_sent", 0),
        ):
            result = await _send_slack_message("Hello")

        assert result is True

    @pytest.mark.asyncio
    async def test_bot_api_timeout(self):
        mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
        mock_client_instance.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(_PATCH_BOT_TOKEN, "xoxb-test-token"),
            patch(_PATCH_BOT_CHANNEL, "C001"),
            patch("orchestrator.tools.notify.httpx.AsyncClient", return_value=mock_client_instance),
        ):
            result = await _send_slack_message("Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_no_bot_token_returns_false(self):
        with (
            patch(_PATCH_BOT_TOKEN, ""),
            patch(_PATCH_BOT_CHANNEL, ""),
        ):
            result = await _send_slack_message("Hello")

        assert result is False


class TestNotifyHuman:
    @pytest.mark.asyncio
    async def test_level_prefix_info(self):
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            result = await do_notify_human({"message": "test", "level": "info"})

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["sent"] is True
        assert data["channel"] == "slack"
        call_text = mock_send.call_args[0][0]
        assert call_text.startswith("\u2139\ufe0f")

    @pytest.mark.asyncio
    async def test_level_prefix_warning(self):
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": "test", "level": "warning"})

        call_text = mock_send.call_args[0][0]
        assert call_text.startswith("\u26a0\ufe0f")

    @pytest.mark.asyncio
    async def test_level_prefix_critical(self):
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": "test", "level": "critical"})

        call_text = mock_send.call_args[0][0]
        assert call_text.startswith("\U0001f6a8")

    @pytest.mark.asyncio
    async def test_truncation(self):
        long_message = "x" * 5000

        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": long_message, "level": "info"})

        call_text = mock_send.call_args[0][0]
        assert len(call_text) <= 4010  # SLACK_MAX_MESSAGE_LENGTH + prefix + "(truncated)"
        assert "(truncated)" in call_text

    @pytest.mark.asyncio
    async def test_fallback_to_log(self):
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await do_notify_human({"message": "test", "level": "info"})

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["sent"] is False
        assert data["channel"] == "log_only"

    @pytest.mark.asyncio
    async def test_kst_timestamp(self):
        """Timestamp should use KST, not UTC."""
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": "test", "level": "info"})

        blocks = mock_send.call_args[1].get("blocks") or mock_send.call_args[0][1]
        context = [b for b in blocks if b["type"] == "context"][0]
        assert "KST" in context["elements"][0]["text"]
        assert "UTC" not in context["elements"][0]["text"]


class TestNotifyWithLinks:
    @pytest.mark.asyncio
    async def test_with_links(self):
        """Links should produce an actions block with buttons."""
        links = [
            {"text": "PR #176", "url": "https://github.com/test/pull/176"},
            {"text": "Actions", "url": "https://github.com/test/actions"},
        ]
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": "test", "level": "info", "links": links})

        blocks = mock_send.call_args[1].get("blocks") or mock_send.call_args[0][1]
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 1
        assert len(actions[0]["elements"]) == 2
        assert actions[0]["elements"][0]["text"]["text"] == "PR #176"

    @pytest.mark.asyncio
    async def test_without_links(self):
        """No links → no actions block (backward compatible)."""
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": "test", "level": "info"})

        blocks = mock_send.call_args[1].get("blocks") or mock_send.call_args[0][1]
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_links_max_5(self):
        """More than 5 links → only first 5 rendered."""
        links = [{"text": f"Link {i}", "url": f"https://example.com/{i}"} for i in range(8)]
        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await do_notify_human({"message": "test", "level": "info", "links": links})

        blocks = mock_send.call_args[1].get("blocks") or mock_send.call_args[0][1]
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
    async def test_format(self):
        summary = {
            "completed_prs": ["#65 (SP-067)"],
            "in_progress": ["SP-069 (running)"],
            "blockers": [],
            "sentry_issues": {"open": 2, "autofix_prs": 1},
        }

        with patch(
            "orchestrator.tools.notify._send_slack_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            result = await send_daily_report(summary)

        assert result is True
        call_text = mock_send.call_args[0][0]
        assert "Coding Machine Report" in call_text
        # PR details are in blocks, not fallback text
        blocks = mock_send.call_args[1].get("blocks") or mock_send.call_args[0][1]
        block_text = json.dumps(blocks)
        assert "#65" in block_text
        assert "SP-069" in block_text
