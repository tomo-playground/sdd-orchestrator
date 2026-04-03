"""Orchestrator decision rules: auto-merge and auto-approval."""

from __future__ import annotations

import re

# ── Auto-Merge Rules (SP-067) ──────────────────────────────


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


# ── Auto-Approval Rules (SP-068) ──────────────────────────

# Patterns that indicate DB schema changes
_DB_PATTERNS = re.compile(r"models/.*\.py|alembic/")

# Patterns that indicate new external dependencies
_DEP_PATTERNS = re.compile(
    r"pyproject\.toml|package\.json|package-lock\.json"
    r"|requirements.*\.txt|poetry\.lock|yarn\.lock|uv\.lock"
)

# BLOCKER marker in markdown bold
_BLOCKER_RE = re.compile(r"\*\*BLOCKER\*\*", re.IGNORECASE)

# Table row pattern: | `path/to/file.ext` | ... | — must contain / or . to be a file path
_TABLE_ROW_RE = re.compile(r"^\|\s*`([^`]+(?:/|\.)[^`]+)`\s*\|", re.MULTILINE)

# Matches '## 변경 파일 요약' section up to the next ## heading or end of file
_CHANGED_FILES_SECTION_RE = re.compile(
    r"##\s*변경\s*파일\s*요약(.*?)(?=\n##|\Z)",
    re.DOTALL,
)


def _extract_changed_files(design_md: str) -> list[str]:
    """Extract file paths from '변경 파일 요약' section only.

    Scans only the changed-files summary table to avoid false positives
    from code examples or other tables (e.g. `httpx.ConnectError`, `/api/chat`).
    Falls back to 7+ files (conservative) if section or parsing fails.
    """
    section_match = _CHANGED_FILES_SECTION_RE.search(design_md)
    if not section_match:
        return ["_parse_failed"] * 7  # conservative fallback
    files = _TABLE_ROW_RE.findall(section_match.group(1))
    return files if files else ["_parse_failed"] * 7  # conservative fallback


def can_auto_approve(design_md: str) -> tuple[bool, str]:
    """Evaluate whether a design can be auto-approved.

    Returns (approved, reason).
    Conditions for auto-approval (all must be true):
    1. No **BLOCKER** markers
    2. Changed files <= MAX_AUTO_APPROVE_FILES (6)
    3. No DB schema changes (models/*.py, alembic/)
    4. No external dependency additions (pyproject.toml, package.json, etc.)
    """
    from sdd_orchestrator.config import MAX_AUTO_APPROVE_FILES

    # 1. BLOCKER check
    if _BLOCKER_RE.search(design_md):
        return False, "BLOCKER found in design"

    # 2. File count check
    files = _extract_changed_files(design_md)
    if not files:
        # Conservative: if we can't parse the table, reject
        return False, "cannot parse changed-files table"

    if len(files) > MAX_AUTO_APPROVE_FILES:
        return False, f"too many files: {len(files)} > {MAX_AUTO_APPROVE_FILES}"

    # 3. DB schema check
    db_files = [f for f in files if _DB_PATTERNS.search(f)]
    if db_files:
        return False, f"DB schema change detected: {', '.join(db_files)}"

    # 4. External dependency check
    dep_files = [f for f in files if _DEP_PATTERNS.search(f)]
    if dep_files:
        return False, f"external dependency change: {', '.join(dep_files)}"

    return True, f"auto-approved: {len(files)} files, no blocker"
