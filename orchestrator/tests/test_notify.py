"""Unit tests for Slack notification tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from orchestrator.tools.notify import _send_slack_message, do_notify_human, send_daily_report


class TestSendSlackMessage:
    @pytest.mark.asyncio
    async def test_success(self):
        response = httpx.Response(200, text="ok")
        mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
        mock_client_instance.post.return_value = response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("orchestrator.tools.notify.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"),
            patch("orchestrator.tools.notify.httpx.AsyncClient", return_value=mock_client_instance),
            patch("orchestrator.tools.notify._last_slack_sent", 0),
        ):
            result = await _send_slack_message("Hello")

        assert result is True

    @pytest.mark.asyncio
    async def test_timeout(self):
        mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
        mock_client_instance.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("orchestrator.tools.notify.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"),
            patch("orchestrator.tools.notify.httpx.AsyncClient", return_value=mock_client_instance),
        ):
            result = await _send_slack_message("Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_no_webhook_url(self):
        with patch("orchestrator.tools.notify.SLACK_WEBHOOK_URL", ""):
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
        assert "SDD Daily Report" in call_text
        assert "#65" in call_text
        assert "SP-069" in call_text
