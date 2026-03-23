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


async def _send_slack_message(text: str) -> bool:
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

    timeout = httpx.Timeout(
        connect=SLACK_TIMEOUT_CONNECT, read=SLACK_TIMEOUT_READ, write=5.0, pool=5.0
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json={"text": text})
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


async def do_notify_human(args: dict) -> dict:
    """Core logic: send a notification to the human via Slack."""
    message = args.get("message", "")
    level = args.get("level", "info")

    emoji = _LEVEL_EMOJI.get(level, "\u2139\ufe0f")
    text = f"{emoji} {message}"

    # Truncate if too long
    if len(text) > SLACK_MAX_MESSAGE_LENGTH:
        text = text[: SLACK_MAX_MESSAGE_LENGTH - 12] + " (truncated)"

    sent = await _send_slack_message(text)
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
    """Format and send a daily report to Slack."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    completed = summary.get("completed_prs", [])
    in_progress = summary.get("in_progress", [])
    blockers = summary.get("blockers", [])
    sentry = summary.get("sentry_issues", {})

    lines = [
        f"\U0001f4cb *SDD Daily Report* \u2014 {today}",
        "",
    ]

    if completed:
        lines.append(f"\u2705 *\uc644\ub8cc PR*: {', '.join(completed)}")
    else:
        lines.append("\u2705 *\uc644\ub8cc PR*: \uc5c6\uc74c")

    if in_progress:
        lines.append(f"\U0001f504 *\uc9c4\ud589 \uc911*: {', '.join(in_progress)}")
    else:
        lines.append("\U0001f504 *\uc9c4\ud589 \uc911*: \uc5c6\uc74c")

    if blockers:
        lines.append(f"\U0001f6ab *\ube14\ub85c\ucee4*: {', '.join(blockers)}")

    sentry_open = sentry.get("open", 0)
    sentry_prs = sentry.get("autofix_prs", 0)
    lines.append(f"\U0001f41b *Sentry*: {sentry_open}\uac74 open, {sentry_prs}\uac74 autofix PR")

    text = "\n".join(lines)
    return await _send_slack_message(text)
