"""Unit tests for auto-merge rules."""

from __future__ import annotations

from orchestrator.rules import can_auto_merge


class TestCanAutoMerge:
    def test_all_pass(self):
        pr = {"ci_status": "success", "review": "APPROVED"}
        ok, reason = can_auto_merge(pr)
        assert ok is True
        assert "passed" in reason.lower()

    def test_ci_failure(self):
        pr = {"ci_status": "failure", "review": "APPROVED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "CI" in reason

    def test_ci_pending(self):
        pr = {"ci_status": "pending", "review": "APPROVED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "CI" in reason

    def test_no_review(self):
        pr = {"ci_status": "success", "review": None}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "review" in reason.lower()

    def test_changes_requested(self):
        pr = {"ci_status": "success", "review": "CHANGES_REQUESTED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "Changes requested" in reason

    def test_review_pending(self):
        pr = {"ci_status": "success", "review": "REVIEW_REQUIRED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False

    def test_empty_dict(self):
        ok, reason = can_auto_merge({})
        assert ok is False
