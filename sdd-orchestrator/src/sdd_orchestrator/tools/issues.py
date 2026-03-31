"""GitHub Issue → SDD Task bridge — scan open issues and auto-create tasks."""

from __future__ import annotations

import asyncio
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
_create_lock = asyncio.Lock()


def set_state_store(store) -> None:
    """Inject the shared StateStore instance (called from main.py)."""
    global _state_store
    _state_store = store


# ── Helpers ──────────────────────────────────────────────────


async def _fetch_labeled_issues(label: str) -> tuple[list[dict], str | None]:
    """Fetch open issues with a single label via gh CLI.

    Returns (issues, error) where error is None on success.
    """
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
        return [], result["error"]
    return result.get("data", []), None


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


def _generate_spec_content(
    task_id: str,
    title: str,
    priority: str,
    description: str,
    issue_number: int,
    branch_slug: str,
) -> str:
    """Generate spec.md content for a new task."""
    body_section = f"\n{description}\n" if description else "\n상세 정보 없음\n"
    return (
        f"# {task_id}: {title}\n"
        f"\n"
        f"- **branch**: feat/{task_id}_{branch_slug}\n"
        f"- **priority**: {priority}\n"
        f"- **scope**: tbd\n"
        f"- **assignee**: AI\n"
        f"- **created**: {today_str()}\n"
        f"- **gh_issue**: #{issue_number}\n"
        f"\n"
        f"## 배경\n"
        f"\n"
        f"GitHub Issue #{issue_number}에서 자동 생성.\n"
        f"{body_section}"
        f"\n"
        f"## DoD (Definition of Done)\n"
        f"\n"
        f"1. Issue #{issue_number}에서 보고된 문제 수정\n"
    )


def _create_task_directory(
    slug: str,
    current_dir: Path,
    done_dir: Path,
    backlog_path: Path,
) -> tuple[Path | None, str | None, str | None]:
    """Create task directory, retrying on SP number collision.

    Returns (task_dir, task_id, error_message).
    """
    for _ in range(5):
        sp_num = next_sp_number(current_dir, done_dir, backlog_path)
        task_id = f"SP-{sp_num:03d}"
        candidate = current_dir / f"{task_id}_{slug}"
        try:
            candidate.mkdir()
            return candidate, task_id, None
        except FileExistsError:
            continue
    return None, None, "태스크 생성 충돌이 반복되어 중단했습니다."


async def _commit_and_register(
    task_id: str,
    task_dir: Path,
    spec_path: Path,
    issue_number: int,
) -> str | None:
    """Commit spec.md then register task status. Returns error string or None."""
    err = await git_commit_files(
        [str(spec_path)],
        f"chore: {task_id} 태스크 자동 생성 (Issue #{issue_number})",
    )
    if err:
        shutil.rmtree(task_dir, ignore_errors=True)
        return f"Git 커밋 실패: {err}"
    _state_store.set_task_status(task_id, "pending")
    return None


# ── Core Logic ───────────────────────────────────────────────


async def do_scan_issues(
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
) -> dict:
    """Scan GitHub Issues (sentry/bug) for unlinked tasks."""
    all_issues: dict[int, dict] = {}
    fetch_errors: list[str] = []

    for label in sorted(ALLOWED_LABELS):
        issues, err = await _fetch_labeled_issues(label)
        if err:
            fetch_errors.append(f"{label}: {err}")
        for issue in issues:
            num = issue.get("number")
            if num is not None:
                all_issues[num] = issue

    existing = _get_existing_issue_mappings(current_dir, done_dir)
    unlinked = [issue for num, issue in sorted(all_issues.items()) if num not in existing]

    result: dict = {
        "unlinked_issues": unlinked,
        "total_open": len(all_issues),
        "already_linked": len(all_issues) - len(unlinked),
    }
    if fetch_errors:
        result["fetch_errors"] = fetch_errors
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
        return _error("StateStore가 초기화되지 않았습니다")

    issue_number = issue.get("number")
    if issue_number is None:
        return _error("Issue number가 없습니다")

    async with _create_lock:
        existing = _get_existing_issue_mappings(current_dir, done_dir)
        if issue_number in existing:
            return _ok(json.dumps({"skipped": True, "reason": "already linked"}))

        title = _extract_title(issue)
        priority = _determine_priority(issue)
        description = _extract_description(issue)
        slug = generate_slug(title)
        current_dir.mkdir(parents=True, exist_ok=True)

        task_dir, task_id, dir_err = _create_task_directory(
            slug, current_dir, done_dir, backlog_path or BACKLOG_PATH
        )
        if dir_err:
            return _error(dir_err)

        branch_slug = generate_slug(title, max_len=30)
        spec_path = task_dir / "spec.md"
        spec_path.write_text(
            _generate_spec_content(
                task_id, title, priority, description, issue_number, branch_slug
            ),
            encoding="utf-8",
        )

        commit_err = await _commit_and_register(task_id, task_dir, spec_path, issue_number)
        if commit_err:
            return _error(commit_err)

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
