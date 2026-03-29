"""Backlog scanner tool — parses .claude/tasks/backlog.md and task specs."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from claude_agent_sdk import tool

from sdd_orchestrator.config import BACKLOG_PATH, TASKS_CURRENT_DIR
from sdd_orchestrator.tools.task_utils import parse_spec_status

logger = logging.getLogger(__name__)

# ── Patterns ───────────────────────────────────────────────
SECTION_RE = re.compile(r"^##\s+(.+)$")
TASK_RE = re.compile(r"^-\s+\[\s*\]\s+(SP-\d+)\s*—\s*(.+)$")
DEPENDS_RE = re.compile(r"depends:\s*(.+?)(?:\||$)")
SCOPE_RE = re.compile(r"scope:\s*(\w+)")
APPROVED_RE = re.compile(r"\*\*approved\*\*", re.IGNORECASE)
PRIORITY_SECTIONS = {"P0", "P1", "P2", "P3", "P2-SDD"}


@dataclass
class BacklogTask:
    id: str
    priority: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    scope: str = ""
    backlog_approved: bool = False
    spec_status: str = "backlog_only"
    has_design: bool = False
    open_pr: str = ""


def parse_backlog(
    backlog_path: Path = BACKLOG_PATH,
    current_dir: Path | None = None,
) -> list[BacklogTask]:
    """Parse backlog.md into a list of tasks with metadata."""
    if not backlog_path.exists():
        logger.warning("backlog.md not found at %s", backlog_path)
        return []

    tasks_dir = current_dir if current_dir is not None else TASKS_CURRENT_DIR

    text = backlog_path.read_text(encoding="utf-8")
    tasks: list[BacklogTask] = []
    current_priority = ""
    in_done_section = False

    for line in text.splitlines():
        section_match = SECTION_RE.match(line.strip())
        if section_match:
            section_name = section_match.group(1).strip()
            # Extract priority key (e.g. "P0 (진행 중)" → "P0")
            section_key = section_name.split()[0] if section_name.split() else section_name
            if section_key in PRIORITY_SECTIONS:
                current_priority = section_key
                in_done_section = False
            elif "완료" in section_name:
                in_done_section = True
                current_priority = ""
            else:
                in_done_section = False
                current_priority = ""
            continue

        if in_done_section or not current_priority:
            continue

        task_match = TASK_RE.match(line.strip())
        if not task_match:
            continue

        task_id = task_match.group(1)
        rest = task_match.group(2)

        depends: list[str] = []
        dep_match = DEPENDS_RE.search(rest)
        if dep_match:
            raw = dep_match.group(1)
            depends = [d.strip() for d in re.findall(r"SP-\d+", raw)]

        scope = ""
        scope_match = SCOPE_RE.search(rest)
        if scope_match:
            scope = scope_match.group(1)

        backlog_approved = bool(APPROVED_RE.search(rest))

        # Clean description: remove metadata pipes
        desc_parts = rest.split("|")
        description = desc_parts[0].strip()
        # Remove trailing markdown links
        description = re.sub(r"\s*\[.*?\]\(.*?\)\s*$", "", description)

        tasks.append(
            BacklogTask(
                id=task_id,
                priority=current_priority,
                description=description,
                depends_on=depends,
                scope=scope,
                backlog_approved=backlog_approved,
            )
        )

    # Enrich with spec/design status from current/ directory
    _enrich_from_specs(tasks, tasks_dir)
    # Discover tasks in current/ that aren't in backlog.md
    _discover_current_tasks(tasks, tasks_dir)
    # Enrich running tasks with PR status (LLM이 교차 매칭 없이 판단 가능)
    _enrich_pr_status(tasks)
    return tasks


def _enrich_from_specs(tasks: list[BacklogTask], tasks_dir: Path = TASKS_CURRENT_DIR) -> None:
    """Check current/ directory for spec.md and design.md per task."""
    if not tasks_dir.exists():
        return

    for task in tasks:
        # Directory pattern: SP-NNN_*/spec.md
        matches = list(tasks_dir.glob(f"{task.id}_*/spec.md"))
        if not matches:
            continue

        spec_path = matches[0]
        task.has_design = (spec_path.parent / "design.md").exists()

        try:
            content = spec_path.read_text(encoding="utf-8")
            task.spec_status = parse_spec_status(content)
        except OSError:
            logger.warning("Failed to read spec: %s", spec_path)


def _discover_current_tasks(tasks: list[BacklogTask], tasks_dir: Path = TASKS_CURRENT_DIR) -> None:
    """Scan current/ for tasks not in backlog.md (e.g. already moved to current/)."""
    if not tasks_dir.exists():
        return

    known_ids = {t.id for t in tasks}

    for spec_path in tasks_dir.glob("SP-*_*/spec.md"):
        task_id = spec_path.parent.name.split("_")[0]
        if task_id in known_ids:
            continue

        # Parse spec frontmatter
        status = "pending"
        priority = "P0"
        description = (
            spec_path.parent.name.split("_", 1)[1].replace("-", " ")
            if "_" in spec_path.parent.name
            else ""
        )
        scope = ""
        depends: list[str] = []

        try:
            content = spec_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                # Strip list prefix, blockquote, and bold markers
                stripped = re.sub(r"^[-*]\s+", "", line)
                stripped = re.sub(r"^>\s*", "", stripped)
                stripped = stripped.replace("**", "")
                if stripped.startswith("status:"):
                    # Handle "status: approved | approved_at: ..."
                    raw_status = stripped.split(":", 1)[1].strip()
                    status = raw_status.split("|")[0].strip()
                elif stripped.startswith("priority:"):
                    priority = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("scope:"):
                    scope = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("depends_on:"):
                    raw = stripped.split(":", 1)[1].strip()
                    depends = [d.strip() for d in re.findall(r"SP-\d+", raw)]
                elif line.startswith("---") and status != "pending":
                    break  # Past frontmatter
        except OSError:
            logger.warning("Failed to read spec: %s", spec_path)
            continue

        has_design = (spec_path.parent / "design.md").exists()

        tasks.append(
            BacklogTask(
                id=task_id,
                priority=priority,
                description=description,
                depends_on=depends,
                scope=scope,
                backlog_approved=False,
                spec_status=status,
                has_design=has_design,
            )
        )
        logger.info("Discovered current/ task: %s (status=%s)", task_id, status)


def _enrich_pr_status(tasks: list[BacklogTask]) -> None:
    """Enrich running tasks with open/merged PR info.

    한 번의 gh 호출로 모든 running 태스크의 PR 상태를 매칭.
    LLM이 check_prs 결과와 교차 매칭할 필요 없이 scan_backlog만으로 판단 가능.
    """
    import subprocess

    from sdd_orchestrator.tools.github import _repo_args

    repo = _repo_args()

    running_tasks = [t for t in tasks if t.spec_status == "running"]
    if not running_tasks:
        return

    # open + merged PR을 한 번에 조회
    for state in ("open", "merged"):
        try:
            r = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    state,
                    "--limit",
                    "50",
                    "--json",
                    "number,headRefName",
                    *repo,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode != 0 or not r.stdout.strip():
                continue
            prs = json.loads(r.stdout)
        except Exception:
            logger.warning("Failed to list %s PRs for enrichment", state, exc_info=True)
            continue

        for pr in prs:
            branch = pr.get("headRefName", "")
            match = re.search(r"SP-\d+", branch)
            if not match:
                continue
            pr_task_id = match.group()
            for task in running_tasks:
                if task.id == pr_task_id and not task.open_pr:
                    label = f"PR #{pr['number']}"
                    if state == "merged":
                        label += " (merged)"
                    task.open_pr = label


@tool("scan_backlog", "Parse backlog.md and task specs to get the full task queue", {})
async def scan_backlog(args: dict) -> dict:
    """MCP tool: scan backlog and return structured task data."""
    try:
        tasks = parse_backlog()
        result = [asdict(t) for t in tasks]
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    except Exception as e:
        logger.exception("scan_backlog failed")
        return {
            "content": [{"type": "text", "text": f"Error scanning backlog: {e}"}],
            "isError": True,
        }
