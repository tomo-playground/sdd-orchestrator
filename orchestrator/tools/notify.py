"""Slack notification tool — send messages and daily reports."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

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

KST = timezone(timedelta(hours=9))

_last_slack_sent: float = 0

_LEVEL_EMOJI = {
    "info": "\u2139\ufe0f",
    "warning": "\u26a0\ufe0f",
    "critical": "\U0001f6a8",
}


async def _send_slack_message(text: str, blocks: list | None = None) -> bool:
    """Send a message to Slack. Prefers Bot Token API, falls back to Webhook."""
    global _last_slack_sent  # noqa: PLW0603

    from orchestrator.config import SLACK_BOT_ALLOWED_CHANNEL, SLACK_BOT_TOKEN

    use_bot = bool(SLACK_BOT_TOKEN and SLACK_BOT_ALLOWED_CHANNEL)

    if not use_bot and not SLACK_WEBHOOK_URL:
        logger.info("Slack not configured, logging only: %s", text[:200])
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
            if use_bot:
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
            else:
                payload = {"text": text}
                if blocks:
                    payload["blocks"] = blocks
                resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
                _last_slack_sent = time.monotonic()
                if resp.status_code == 200:
                    return True
                logger.warning("Slack webhook error %d: %s", resp.status_code, resp.text[:200])
                return False
    except httpx.TimeoutException:
        logger.warning("Slack send timeout")
        return False
    except Exception:
        logger.exception("Slack send error")
        return False


_LEVEL_COLOR = {
    "info": "#2196F3",
    "warning": "#FF9800",
    "critical": "#F44336",
}


def _build_link_buttons(links: list[dict]) -> dict | None:
    """Build a Block Kit actions block from a list of link dicts."""
    if not links:
        return None
    elements = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": link["text"][:75]},
            "url": link["url"],
        }
        for link in links[:5]
    ]
    return {"type": "actions", "elements": elements}


async def do_notify_human(args: dict) -> dict:
    """Core logic: send a notification to the human via Slack."""
    message = args.get("message", "")
    level = args.get("level", "info")
    links = args.get("links", [])

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
                    "text": f"Coding Machine — {datetime.now(KST).strftime('%H:%M KST')}",
                },
            ],
        },
    ]

    actions_block = _build_link_buttons(links)
    if actions_block:
        blocks.append(actions_block)

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
    today = datetime.now(KST).strftime("%Y-%m-%d")

    completed = summary.get("completed_prs", [])
    in_progress = summary.get("in_progress", [])
    open_prs = summary.get("open_prs", [])
    blockers = summary.get("blockers", [])
    slots = summary.get("slots", "?/?")
    sentry = summary.get("sentry_issues", {})
    sentry_open = sentry.get("open", 0)

    def _fmt_list(items: list, limit: int = 5) -> str:
        if not items:
            return "—"
        return "\n".join(f"• {x}" for x in items[:limit])

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Coding Machine Report — {today}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*머지 완료*\n{_fmt_list(completed)}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*열린 PR*\n{_fmt_list(open_prs)}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*진행 중 태스크*\n{_fmt_list(in_progress)}"},
                {"type": "mrkdwn", "text": f"*슬롯*\n{slots}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*블로커*\n{_fmt_list(blockers)}"},
                {"type": "mrkdwn", "text": f"*Sentry*\n{sentry_open}건 미해결"},
            ],
        },
    ]

    fallback = (
        f"Coding Machine Report {today}: "
        f"머지 {len(completed)}건, PR {len(open_prs)}건, "
        f"태스크 {len(in_progress)}건, 슬롯 {slots}, Sentry {sentry_open}건"
    )
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
