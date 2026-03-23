"""Backlog scanner tool — parses .claude/tasks/backlog.md and task specs."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from claude_agent_sdk import tool

from orchestrator.config import BACKLOG_PATH, TASKS_CURRENT_DIR

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


def parse_backlog(backlog_path: Path = BACKLOG_PATH) -> list[BacklogTask]:
    """Parse backlog.md into a list of tasks with metadata."""
    if not backlog_path.exists():
        logger.warning("backlog.md not found at %s", backlog_path)
        return []

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
    _enrich_from_specs(tasks)
    return tasks


def _enrich_from_specs(tasks: list[BacklogTask]) -> None:
    """Check current/ directory for spec.md and design.md per task."""
    if not TASKS_CURRENT_DIR.exists():
        return

    for task in tasks:
        # Directory pattern: SP-NNN_*/spec.md
        matches = list(TASKS_CURRENT_DIR.glob(f"{task.id}_*/spec.md"))
        if not matches:
            continue

        spec_path = matches[0]
        task.has_design = (spec_path.parent / "design.md").exists()

        # Parse frontmatter status
        try:
            content = spec_path.read_text(encoding="utf-8")
            status_match = re.search(r"^status:\s*(\w+)", content, re.MULTILINE)
            if status_match:
                task.spec_status = status_match.group(1)
        except OSError:
            logger.warning("Failed to read spec: %s", spec_path)


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
            "is_error": True,
        }
