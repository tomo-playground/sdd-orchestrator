"""Slack Block Kit helpers and message templates.

Separates message *composition* (what) from *delivery* (how).
All functions are pure — no side effects, no Slack API calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orchestrator.config import (
    SLACK_BLOCK_BUDGET,
    SLACK_BLOCK_TEXT_MAX,
    SLACK_BUTTON_TEXT_MAX,
    SLACK_MAX_MESSAGE_LENGTH,
)

KST = timezone(timedelta(hours=9))

_LEVEL_EMOJI = {
    "info": "\u2139\ufe0f",
    "warning": "\u26a0\ufe0f",
    "critical": "\U0001f6a8",
}

# ── Block Kit Helpers ────────────────────────────────────────


def header_block(text: str) -> dict:
    """Plain-text header block."""
    return {"type": "header", "text": {"type": "plain_text", "text": text}}


def section_block(text: str) -> dict:
    """Mrkdwn section block."""
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def divider() -> dict:
    """Divider block."""
    return {"type": "divider"}


def context_block(text: str) -> dict:
    """Mrkdwn context block."""
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": text}],
    }


def link_buttons(links: list[dict], max_count: int = 5) -> dict | None:
    """Build an actions block from link dicts. Returns None if empty."""
    if not links:
        return None
    elements = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": link["text"][:SLACK_BUTTON_TEXT_MAX]},
            "url": link["url"] if link["url"].startswith(("https://", "http://")) else "#",
        }
        for link in links[:max_count]
    ]
    return {"type": "actions", "elements": elements}


def blocks_to_fallback(blocks: list[dict], max_len: int = 200) -> str:
    """Extract plain text from blocks for the fallback field."""
    parts = []
    for b in blocks:
        if b.get("type") == "header":
            parts.append(b.get("text", {}).get("text", ""))
        elif b.get("type") == "section":
            parts.append(b.get("text", {}).get("text", ""))
    return "\n".join(parts)[:max_len]


# ── Message Templates ────────────────────────────────────────


def notification_blocks(
    level: str,
    message: str,
    links: list[dict] | None = None,
) -> tuple[list[dict], str]:
    """Build notification blocks + fallback text.

    Returns:
        (blocks, fallback) tuple.
    """
    emoji = _LEVEL_EMOJI.get(level, "\u2139\ufe0f")
    fallback = f"{emoji} {message}"

    if len(fallback) > SLACK_MAX_MESSAGE_LENGTH:
        fallback = fallback[: SLACK_MAX_MESSAGE_LENGTH - 12] + " (truncated)"

    section_text = f"{emoji} *[{level.upper()}]* {message}"
    if len(section_text) > SLACK_BLOCK_TEXT_MAX:
        section_text = section_text[: SLACK_BLOCK_TEXT_MAX - 1] + "\u2026"

    blocks: list[dict] = [
        section_block(section_text),
        context_block(f"Coding Machine \u2014 {datetime.now(KST).strftime('%H:%M KST')}"),
    ]

    actions = link_buttons(links or [])
    if actions:
        blocks.append(actions)

    return blocks, fallback


def daily_report_blocks(summary: dict) -> tuple[list[dict], str]:
    """Build daily report blocks + fallback text."""
    today = datetime.now(KST).strftime("%Y-%m-%d")

    completed = summary.get("completed_prs", [])
    in_progress = summary.get("in_progress", [])
    open_prs = summary.get("open_prs", [])
    blockers = summary.get("blockers", [])
    slots = summary.get("slots", "?/?")
    sentry = summary.get("sentry_issues", {})
    sentry_open = sentry.get("open", 0)
    rollbacks = summary.get("rollbacks", [])

    def _fmt_list(items: list, limit: int = 5) -> str:
        if not items:
            return "\u2014"
        return "\n".join(f"\u2022 {x}" for x in items[:limit])

    blocks: list[dict] = [
        header_block(f"Coding Machine Report \u2014 {today}"),
        divider(),
        section_block(f"*\uba38\uc9c0 \uc644\ub8cc*\n{_fmt_list(completed)}"),
        section_block(f"*\uc5f4\ub9b0 PR*\n{_fmt_list(open_prs)}"),
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*\uc9c4\ud589 \uc911 \ud0dc\uc2a4\ud06c*\n{_fmt_list(in_progress)}",
                },
                {"type": "mrkdwn", "text": f"*\uc2ac\ub86f*\n{slots}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*\ube14\ub85c\ucee4*\n{_fmt_list(blockers)}"},
                {"type": "mrkdwn", "text": f"*Sentry*\n{sentry_open}\uac74 \ubbf8\ud574\uacb0"},
            ],
        },
    ]

    if rollbacks:
        rb_items = [
            f"PR #{rb.get('original_pr', '?')} \u2192 {rb.get('status', '?')}"
            if isinstance(rb, dict)
            else str(rb)
            for rb in rollbacks[:5]
        ]
        blocks.append(section_block(f"*\ub864\ubc31*\n{_fmt_list(rb_items)}"))

    fallback = (
        f"Coding Machine Report {today}: "
        f"\uba38\uc9c0 {len(completed)}\uac74, PR {len(open_prs)}\uac74, "
        f"\ud0dc\uc2a4\ud06c {len(in_progress)}\uac74, \uc2ac\ub86f {slots}, Sentry {sentry_open}\uac74"
    )
    return blocks, fallback


def error_blocks(message: str) -> list[dict]:
    """Error message blocks (header + section)."""
    return [
        header_block("\uc624\ub958"),
        section_block(f":warning: {message}"),
    ]


def agent_response_blocks(text: str) -> list[dict]:
    """Convert agent text response to Block Kit blocks.

    Splits on double newlines into multiple section blocks with dividers.
    Each section is capped at 3000 chars (Slack limit).
    """
    sections = [s.strip() for s in text.split("\n\n") if s.strip()]

    if not sections:
        return [section_block("(\ube48 \uc751\ub2f5)")]

    blocks: list[dict] = []
    total_chars = 0

    for i, sec in enumerate(sections):
        if total_chars + len(sec) > SLACK_BLOCK_BUDGET:
            remaining = SLACK_BLOCK_BUDGET - total_chars
            if remaining > 50:
                blocks.append(section_block(sec[:remaining] + "\u2026"))
            break
        if i > 0:
            blocks.append(divider())
        blocks.append(section_block(sec[:SLACK_BLOCK_TEXT_MAX]))
        total_chars += len(sec)

    return blocks
