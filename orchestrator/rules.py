"""Auto-merge rules for the SDD Orchestrator."""

from __future__ import annotations


def can_auto_merge(pr_summary: dict) -> tuple[bool, str]:
    """Determine if a PR can be auto-merged.

    Args:
        pr_summary: PR summary dict from summarize_prs() with keys:
            ci_status, review, mergeable, etc.

    Returns:
        (can_merge, reason) tuple.
    """
    ci = pr_summary.get("ci_status", "")
    review = pr_summary.get("review", "")

    if ci != "success":
        return False, f"CI not passed (status={ci})"

    if review == "CHANGES_REQUESTED":
        return False, "Changes requested by reviewer"

    if review != "APPROVED":
        return False, f"Review not approved (review={review})"

    return True, "All checks passed: CI success + review approved"
