"""Slack notification tool — send messages and daily reports."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

import httpx
from claude_agent_sdk import tool

from orchestrator.config import (
    SLACK_MAX_MESSAGE_LENGTH,
    SLACK_MIN_INTERVAL,
    SLACK_TIMEOUT_CONNECT,
    SLACK_TIMEOUT_READ,
    SLACK_WEBHOOK_URL,
)

logger = logging.getLogger(__name__)

_last_slack_sent: float = 0

_LEVEL_EMOJI = {
    "info": "\u2139\ufe0f",
    "warning": "\u26a0\ufe0f",
    "critical": "\U0001f6a8",
}


async def _send_slack_message(text: str, blocks: list | None = None) -> bool:
    """Send a message to Slack via webhook. Returns True on success."""
    global _last_slack_sent

    if not SLACK_WEBHOOK_URL:
        logger.info("Slack webhook not configured, logging only: %s", text[:200])
        return False

    # Rate limit guard
    import asyncio

    elapsed = time.monotonic() - _last_slack_sent
    if elapsed < SLACK_MIN_INTERVAL:
        await asyncio.sleep(SLACK_MIN_INTERVAL - elapsed)

    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    timeout = httpx.Timeout(
        connect=SLACK_TIMEOUT_CONNECT, read=SLACK_TIMEOUT_READ, write=5.0, pool=5.0
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
            _last_slack_sent = time.monotonic()
            if resp.status_code == 200:
                return True
            logger.warning("Slack API error %d: %s", resp.status_code, resp.text[:200])
            return False
    except httpx.TimeoutException:
        logger.warning("Slack webhook timeout")
        return False
    except Exception:
        logger.exception("Slack webhook error")
        return False


_LEVEL_COLOR = {
    "info": "#2196F3",
    "warning": "#FF9800",
    "critical": "#F44336",
}


async def do_notify_human(args: dict) -> dict:
    """Core logic: send a notification to the human via Slack."""
    message = args.get("message", "")
    level = args.get("level", "info")

    emoji = _LEVEL_EMOJI.get(level, "\u2139\ufe0f")
    fallback = f"{emoji} {message}"

    # Truncate if too long
    if len(fallback) > SLACK_MAX_MESSAGE_LENGTH:
        fallback = fallback[: SLACK_MAX_MESSAGE_LENGTH - 12] + " (truncated)"

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{emoji} *[{level.upper()}]* {message}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Coding Machine — {datetime.now(UTC).strftime('%H:%M UTC')}",
                },
            ],
        },
    ]

    sent = await _send_slack_message(fallback, blocks)
    channel = "slack" if sent else "log_only"

    if not sent:
        logger.info("[%s] %s", level.upper(), message)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"sent": sent, "channel": channel}),
            }
        ]
    }


@tool(
    "notify_human",
    "Send a notification to Slack (info/warning/critical level)",
    {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to send"},
            "level": {
                "type": "string",
                "enum": ["info", "warning", "critical"],
                "description": "Notification level",
            },
        },
        "required": ["message", "level"],
    },
)
async def notify_human(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_notify_human(args)


async def send_daily_report(summary: dict) -> bool:
    """Format and send a daily report to Slack using Block Kit."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    completed = summary.get("completed_prs", [])
    in_progress = summary.get("in_progress", [])
    blockers = summary.get("blockers", [])
    sentry = summary.get("sentry_issues", {})
    sentry_open = sentry.get("open", 0)
    sentry_prs = sentry.get("autofix_prs", 0)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Coding Machine Report — {today}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Completed*\n{', '.join(completed) if completed else '—'}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*In Progress*\n{', '.join(in_progress) if in_progress else '—'}",
                },
            ],
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Blockers*\n{', '.join(blockers) if blockers else '—'}",
                },
                {"type": "mrkdwn", "text": f"*Sentry*\n{sentry_open} open / {sentry_prs} autofix"},
            ],
        },
    ]

    fallback = f"Coding Machine Report {today}: {len(completed)} completed, {len(in_progress)} in progress, {len(blockers)} blockers, {sentry_open} sentry"
    return await _send_slack_message(fallback, blocks)
