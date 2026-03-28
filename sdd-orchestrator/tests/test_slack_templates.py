"""Unit tests for Slack Block Kit helpers and message templates."""

from __future__ import annotations

from sdd_orchestrator.tools.slack_templates import (
    agent_response_blocks,
    blocks_to_fallback,
    context_block,
    daily_report_blocks,
    divider,
    error_blocks,
    header_block,
    link_buttons,
    notification_blocks,
    section_block,
)

# ── Block Kit Helpers ────────────────────────────────────────


class TestBlockKitHelpers:
    def test_header_block_structure(self):
        result = header_block("Title")
        assert result == {"type": "header", "text": {"type": "plain_text", "text": "Title"}}

    def test_section_block_mrkdwn(self):
        result = section_block("*bold* text")
        assert result == {"type": "section", "text": {"type": "mrkdwn", "text": "*bold* text"}}

    def test_divider(self):
        assert divider() == {"type": "divider"}

    def test_context_block(self):
        result = context_block("footer text")
        assert result["type"] == "context"
        assert result["elements"][0]["type"] == "mrkdwn"
        assert result["elements"][0]["text"] == "footer text"

    def test_link_buttons_empty(self):
        assert link_buttons([]) is None

    def test_link_buttons_single(self):
        result = link_buttons([{"text": "PR", "url": "https://example.com"}])
        assert result["type"] == "actions"
        assert len(result["elements"]) == 1
        assert result["elements"][0]["text"]["text"] == "PR"

    def test_link_buttons_max_5(self):
        links = [{"text": f"L{i}", "url": f"https://example.com/{i}"} for i in range(8)]
        result = link_buttons(links)
        assert len(result["elements"]) == 5

    def test_link_buttons_truncates_label(self):
        result = link_buttons([{"text": "x" * 100, "url": "https://example.com"}])
        assert len(result["elements"][0]["text"]["text"]) == 75

    def test_link_buttons_rejects_invalid_scheme(self):
        result = link_buttons([{"text": "XSS", "url": "javascript:alert(1)"}])
        assert result["elements"][0]["url"] == "#"

    def test_link_buttons_allows_https(self):
        result = link_buttons([{"text": "OK", "url": "https://github.com/test"}])
        assert result["elements"][0]["url"] == "https://github.com/test"

    def test_link_buttons_allows_http(self):
        result = link_buttons([{"text": "OK", "url": "http://internal.example.com"}])
        assert result["elements"][0]["url"] == "http://internal.example.com"

    def test_blocks_to_fallback_header_and_section(self):
        blocks = [header_block("Title"), section_block("Body text")]
        result = blocks_to_fallback(blocks)
        assert "Title" in result
        assert "Body text" in result

    def test_blocks_to_fallback_empty(self):
        assert blocks_to_fallback([]) == ""

    def test_blocks_to_fallback_max_len(self):
        blocks = [section_block("x" * 500)]
        result = blocks_to_fallback(blocks, max_len=100)
        assert len(result) <= 100


# ── Notification Blocks ──────────────────────────────────────


class TestNotificationBlocks:
    def test_info_level(self):
        blocks, fallback = notification_blocks("info", "test message")
        assert "\u2139\ufe0f" in fallback
        section = blocks[0]
        assert "*[INFO]*" in section["text"]["text"]

    def test_warning_level(self):
        blocks, fallback = notification_blocks("warning", "warn")
        assert "\u26a0\ufe0f" in fallback

    def test_critical_level(self):
        blocks, fallback = notification_blocks("critical", "alert")
        assert "\U0001f6a8" in fallback

    def test_with_links(self):
        links = [{"text": "PR #1", "url": "https://github.com/test/pull/1"}]
        blocks, _ = notification_blocks("info", "test", links)
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 1
        assert actions[0]["elements"][0]["text"]["text"] == "PR #1"

    def test_without_links(self):
        blocks, _ = notification_blocks("info", "test")
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 0

    def test_truncation(self):
        blocks, fallback = notification_blocks("info", "x" * 5000)
        assert len(fallback) <= 4010
        assert "(truncated)" in fallback
        # Section block must also respect Slack's 3000-char limit
        assert len(blocks[0]["text"]["text"]) <= 3000
        assert "\u2026" in blocks[0]["text"]["text"]

    def test_kst_timestamp(self):
        blocks, _ = notification_blocks("info", "test")
        context = [b for b in blocks if b["type"] == "context"][0]
        assert "KST" in context["elements"][0]["text"]


# ── Daily Report Blocks ──────────────────────────────────────


class TestDailyReportBlocks:
    def test_full_summary(self):
        summary = {
            "completed_prs": ["#65 (SP-067)"],
            "in_progress": ["SP-069 (running)"],
            "open_prs": ["#70"],
            "blockers": [],
            "slots": "2/3",
            "sentry_issues": {"open": 2},
        }
        blocks, fallback = daily_report_blocks(summary)
        assert "Coding Machine Report" in fallback
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "divider"
        # Verify content is present in blocks
        import json

        block_text = json.dumps(blocks)
        assert "#65" in block_text
        assert "SP-069" in block_text

    def test_empty_summary(self):
        blocks, fallback = daily_report_blocks({})
        assert "Coding Machine Report" in fallback
        assert blocks[0]["type"] == "header"

    def test_with_rollbacks(self):
        summary = {"rollbacks": [{"original_pr": 42, "status": "reverted"}]}
        blocks, _ = daily_report_blocks(summary)
        import json

        block_text = json.dumps(blocks)
        assert "PR #42" in block_text
        assert "reverted" in block_text

    def test_rollbacks_string_items_no_error(self):
        """Non-dict rollback items must not raise AttributeError."""
        summary = {"rollbacks": ["PR #42 reverted", "PR #43 reverted"]}
        blocks, _ = daily_report_blocks(summary)
        import json

        block_text = json.dumps(blocks)
        assert "PR #42 reverted" in block_text

    def test_missing_keys_use_defaults(self):
        blocks, fallback = daily_report_blocks({})
        assert "?/?" in fallback
        assert "0건" in fallback


# ── Error Blocks ─────────────────────────────────────────────


class TestErrorBlocks:
    def test_structure(self):
        blocks = error_blocks("something failed")
        assert len(blocks) == 2
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "section"
        assert "something failed" in blocks[1]["text"]["text"]


# ── Agent Response Blocks ────────────────────────────────────


class TestAgentResponseBlocks:
    def test_single_paragraph(self):
        blocks = agent_response_blocks("Hello world")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "section"
        assert blocks[0]["text"]["text"] == "Hello world"

    def test_multi_paragraph_with_dividers(self):
        blocks = agent_response_blocks("First\n\nSecond\n\nThird")
        sections = [b for b in blocks if b["type"] == "section"]
        dividers = [b for b in blocks if b["type"] == "divider"]
        assert len(sections) == 3
        assert len(dividers) == 2

    def test_empty_text(self):
        blocks = agent_response_blocks("")
        assert len(blocks) == 1
        assert "(빈 응답)" in blocks[0]["text"]["text"]

    def test_long_text_truncation(self):
        long_text = "x" * 3500
        blocks = agent_response_blocks(long_text)
        text = blocks[0]["text"]["text"]
        assert len(text) <= 3000
        assert text.endswith("\u2026")
