"""Slack notification tool — send messages and daily reports."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING

from claude_agent_sdk import tool

from sdd_orchestrator.tools.slack_templates import (
    daily_report_blocks,
    notification_blocks,
)

if TYPE_CHECKING:
    from sdd_orchestrator.tools.slack_bot import SlackBotListener

logger = logging.getLogger(__name__)

# SlackBot 싱글턴 참조 (set by orchestrator main via init_notify)
_bot: SlackBotListener | None = None


def init_notify(bot: SlackBotListener | None) -> None:
    """SlackBot 인스턴스 등록 — 모든 알림이 이 Bot을 경유."""
    global _bot  # noqa: PLW0603
    _bot = bot


async def do_notify_human(args: dict) -> dict:
    """Core logic: send a notification to the human via Slack."""

    message = args.get("message", "")
    level = args.get("level", "info")
    links = args.get("links", [])

    blocks, fallback = notification_blocks(level, message, links)

    ts = None
    if _bot:
        ts = await _bot.post_notification(fallback, blocks)

    channel = "slack" if ts else "log_only"
    if not ts:
        logger.info("[%s] %s", level.upper(), message)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"sent": bool(ts), "channel": channel, "ts": ts}),
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
    if _bot:
        return bool(await _bot.post_notification(fallback, blocks))
    logger.info("SlackBot not available, daily report logged only: %s", fallback[:200])
    return False


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
