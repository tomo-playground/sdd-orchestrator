"""Slack notification tool — send messages and daily reports."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time

import httpx
from claude_agent_sdk import tool

from orchestrator.config import (
    SLACK_MIN_INTERVAL,
    SLACK_TIMEOUT_CONNECT,
    SLACK_TIMEOUT_READ,
)
from orchestrator.tools.slack_templates import (
    daily_report_blocks,
    notification_blocks,
)

logger = logging.getLogger(__name__)

_last_slack_sent: float = 0


async def _send_slack_message(text: str, blocks: list | None = None) -> bool:
    """Send a message to Slack via Bot Token API."""
    global _last_slack_sent  # noqa: PLW0603

    from orchestrator.config import SLACK_BOT_ALLOWED_CHANNEL, SLACK_BOT_TOKEN

    if not SLACK_BOT_TOKEN or not SLACK_BOT_ALLOWED_CHANNEL:
        logger.info("Slack Bot not configured, logging only: %s", text[:200])
        return False

    # Rate limit guard
    elapsed = time.monotonic() - _last_slack_sent
    if elapsed < SLACK_MIN_INTERVAL:
        await asyncio.sleep(SLACK_MIN_INTERVAL - elapsed)

    timeout = httpx.Timeout(
        connect=SLACK_TIMEOUT_CONNECT, read=SLACK_TIMEOUT_READ, write=5.0, pool=5.0
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            payload: dict = {
                "channel": SLACK_BOT_ALLOWED_CHANNEL,
                "text": text,
            }
            if blocks:
                payload["blocks"] = blocks
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            )
            _last_slack_sent = time.monotonic()
            data = resp.json()
            if data.get("ok"):
                return True
            logger.warning("Slack Bot API error: %s", data.get("error", "unknown"))
            return False
    except httpx.TimeoutException:
        logger.warning("Slack send timeout")
        return False
    except Exception:
        logger.exception("Slack send error")
        return False


async def do_notify_human(args: dict) -> dict:
    """Core logic: send a notification to the human via Slack."""

    message = args.get("message", "")
    level = args.get("level", "info")
    links = args.get("links", [])

    blocks, fallback = notification_blocks(level, message, links)

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
            "links": {
                "type": "array",
                "description": "Optional link buttons (max 5)",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Button label"},
                        "url": {"type": "string", "description": "Button URL"},
                    },
                    "required": ["text", "url"],
                },
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

    blocks, fallback = daily_report_blocks(summary)
    return await _send_slack_message(fallback, blocks)


# ── CLI entrypoint ──────────────────────────────────────────


async def _cli_main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Send Slack notification via Block Kit")
    parser.add_argument("message", help="Message text")
    parser.add_argument("--level", default="info", choices=["info", "warning", "critical"])
    parser.add_argument(
        "--link",
        nargs=2,
        action="append",
        metavar=("TEXT", "URL"),
        help="Add a link button (can be repeated)",
    )
    parsed = parser.parse_args()
    links = [{"text": t, "url": u} for t, u in (parsed.link or [])]
    result = await do_notify_human(
        {"message": parsed.message, "level": parsed.level, "links": links}
    )
    try:
        data = json.loads(result["content"][0]["text"])
    except (KeyError, IndexError, json.JSONDecodeError):
        data = {}
    return 0 if data.get("sent", False) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_cli_main()))
