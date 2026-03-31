"""GitHub Issue → SDD Task bridge — scan open issues and auto-create tasks."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path

from claude_agent_sdk import tool

from sdd_orchestrator.config import TASKS_CURRENT_DIR, TASKS_DONE_DIR
from sdd_orchestrator.tools.github import _run_gh_command
from sdd_orchestrator.tools.task_utils import (
    _error,
    _ok,
    generate_slug,
    git_commit_files,
    next_sp_number,
    today_str,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────
ALLOWED_LABELS: frozenset[str] = frozenset({"sentry", "bug"})
ISSUE_FIELDS = "number,title,body,labels,createdAt"
_MAX_BODY_LEN = 4000
_SENTRY_TITLE_RE = re.compile(r"^\[Sentry/[^\]]+\]\s*")
GH_ISSUE_RE = re.compile(r"\*{0,2}gh_issue\*{0,2}:\s*#?(\d+)")

# Module-level StateStore reference, set by set_state_store()
_state_store = None


def set_state_store(store) -> None:
    """Inject the shared StateStore instance (called from main.py)."""
    global _state_store
    _state_store = store


# ── Helpers ──────────────────────────────────────────────────


async def _fetch_labeled_issues(label: str) -> list[dict]:
    """Fetch open issues with a single label via gh CLI."""
    result = await _run_gh_command(
        "issue",
        "list",
        "--label",
        label,
        "--state",
        "open",
        "--json",
        ISSUE_FIELDS,
        "--limit",
        "50",
    )
    if "error" in result:
        logger.warning("Failed to fetch issues with label=%s: %s", label, result["error"])
        return []
    return result.get("data", [])


def _get_existing_issue_mappings(
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
) -> set[int]:
    """Scan current/ + done/ spec.md files for gh_issue: #N metadata."""
    mapped: set[int] = set()
    for tasks_dir in (current_dir, done_dir):
        if not tasks_dir.exists():
            continue
        for spec in tasks_dir.glob("SP-*_*/spec.md"):
            try:
                text = spec.read_text(encoding="utf-8")
                match = GH_ISSUE_RE.search(text)
                if match:
                    mapped.add(int(match.group(1)))
            except OSError:
                continue
    return mapped


def _extract_title(issue: dict) -> str:
    """Extract clean title — strips [Sentry/project] prefix."""
    raw = issue.get("title", "").strip()
    return _SENTRY_TITLE_RE.sub("", raw) or raw


def _extract_description(issue: dict) -> str:
    """Extract issue body, truncated to _MAX_BODY_LEN."""
    body = issue.get("body", "") or ""
    if len(body) > _MAX_BODY_LEN:
        body = body[:_MAX_BODY_LEN] + "\n\n[truncated]"
    return body


def _determine_priority(issue: dict) -> str:
    """Determine priority from labels. sentry > bug."""
    labels = {lbl.get("name", "") for lbl in (issue.get("labels") or [])}
    if "sentry" in labels:
        return "P1"
    return "P2"


# ── Core Logic ───────────────────────────────────────────────


async def do_scan_issues(
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
) -> dict:
    """Scan GitHub Issues (sentry/bug) for unlinked tasks."""
    all_issues: dict[int, dict] = {}

    for label in sorted(ALLOWED_LABELS):
        issues = await _fetch_labeled_issues(label)
        for issue in issues:
            num = issue.get("number")
            if num is not None:
                all_issues[num] = issue

    existing = _get_existing_issue_mappings(current_dir, done_dir)
    unlinked = [issue for num, issue in sorted(all_issues.items()) if num not in existing]

    result = {
        "unlinked_issues": unlinked,
        "total_open": len(all_issues),
        "already_linked": len(all_issues) - len(unlinked),
    }
    return _ok(json.dumps(result, ensure_ascii=False))


async def do_auto_create_task(
    issue: dict,
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
    backlog_path: Path | None = None,
) -> dict:
    """Create an SDD task from a GitHub Issue."""
    from sdd_orchestrator.config import BACKLOG_PATH

    if not _state_store:
        return _error(
            "StateStore\uac00 \ucd08\uae30\ud654\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4"
        )

    issue_number = issue.get("number")
    if issue_number is None:
        return _error("Issue number\uac00 \uc5c6\uc2b5\ub2c8\ub2e4")

    # Double-check: skip if already linked
    existing = _get_existing_issue_mappings(current_dir, done_dir)
    if issue_number in existing:
        return _ok(json.dumps({"skipped": True, "reason": "already linked"}))

    title = _extract_title(issue)
    priority = _determine_priority(issue)
    description = _extract_description(issue)

    current_dir.mkdir(parents=True, exist_ok=True)
    slug = generate_slug(title)

    task_dir = None
    task_id = None
    for _ in range(5):
        sp_num = next_sp_number(current_dir, done_dir, backlog_path or BACKLOG_PATH)
        task_id = f"SP-{sp_num:03d}"
        dir_name = f"{task_id}_{slug}"
        candidate = current_dir / dir_name
        try:
            candidate.mkdir()
            task_dir = candidate
            break
        except FileExistsError:
            continue

    if task_dir is None:
        return _error(
            "\ud0dc\uc2a4\ud06c \uc0dd\uc131 \ucda9\ub3cc\uc774 \ubc18\ubcf5\ub418\uc5b4 \uc911\ub2e8\ud588\uc2b5\ub2c8\ub2e4."
        )

    branch_slug = generate_slug(title, max_len=30)
    body_section = (
        f"\n{description}\n" if description else "\n\uc0c1\uc138 \uc815\ubcf4 \uc5c6\uc74c\n"
    )

    spec_content = (
        f"# {task_id}: {title}\n"
        f"\n"
        f"- **branch**: feat/{task_id}_{branch_slug}\n"
        f"- **priority**: {priority}\n"
        f"- **scope**: backend\n"
        f"- **assignee**: AI\n"
        f"- **created**: {today_str()}\n"
        f"- **gh_issue**: #{issue_number}\n"
        f"\n"
        f"## \ubc30\uacbd\n"
        f"\n"
        f"GitHub Issue #{issue_number}\uc5d0\uc11c \uc790\ub3d9 \uc0dd\uc131.\n"
        f"{body_section}"
        f"\n"
        f"## DoD (Definition of Done)\n"
        f"\n"
        f"1. Issue #{issue_number}\uc5d0\uc11c \ubcf4\uace0\ub41c \ubb38\uc81c \uc218\uc815\n"
    )

    spec_path = task_dir / "spec.md"
    spec_path.write_text(spec_content, encoding="utf-8")

    _state_store.set_task_status(task_id, "pending")

    err = await git_commit_files(
        [str(spec_path)],
        f"chore: {task_id} \ud0dc\uc2a4\ud06c \uc790\ub3d9 \uc0dd\uc131 (Issue #{issue_number})",
    )
    if err:
        shutil.rmtree(task_dir, ignore_errors=True)
        _state_store.delete_task_status(task_id)
        return _error(f"Git \ucee4\ubc0b \uc2e4\ud328: {err}")

    result = {"task_id": task_id, "issue_number": issue_number, "priority": priority}
    return _ok(json.dumps(result, ensure_ascii=False))


# ── MCP Tool Wrappers ────────────────────────────────────────


@tool(
    "scan_issues",
    "Scan open GitHub Issues (sentry/bug labels) for unlinked tasks",
    {},
)
async def scan_issues(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_scan_issues()


@tool(
    "auto_create_task",
    "Create SDD task from a GitHub Issue (spec.md + state.db)",
    {
        "type": "object",
        "properties": {
            "issue": {
                "type": "object",
                "description": "GitHub Issue object with number, title, body, labels",
            },
        },
        "required": ["issue"],
    },
)
async def auto_create_task(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_auto_create_task(args["issue"])
