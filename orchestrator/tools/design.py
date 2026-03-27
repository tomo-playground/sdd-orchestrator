"""Auto-design tool — generates design.md for pending tasks."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from claude_agent_sdk import tool

from orchestrator.agents import build_designer_prompt, create_designer_options
from orchestrator.config import DESIGN_TIMEOUT, TASKS_CURRENT_DIR
from orchestrator.rules import can_auto_approve
from orchestrator.tools.task_utils import parse_spec_status, update_spec_status
from orchestrator.utils import query_agent

logger = logging.getLogger(__name__)


def _find_task_dir(task_id: str) -> Path | None:
    """Find the task directory for an SP-NNN id."""
    if not TASKS_CURRENT_DIR.exists():
        return None
    matches = list(TASKS_CURRENT_DIR.glob(f"{task_id}_*/spec.md"))
    if not matches:
        return None
    return matches[0].parent


def _read_spec_status(task_dir: Path) -> str | None:
    """Read the status from a spec.md (supports frontmatter and blockquote)."""
    spec = task_dir / "spec.md"
    if not spec.exists():
        return None
    content = spec.read_text(encoding="utf-8")
    status = parse_spec_status(content)
    return status if status != "pending" or "status:" in content else None


def _update_spec_status(task_dir: Path, new_status: str) -> None:
    """Update the status field in spec.md."""
    spec = task_dir / "spec.md"
    content = spec.read_text(encoding="utf-8")
    metadata = ""
    if new_status == "approved":
        metadata = f"approved_at: {datetime.now(UTC).strftime('%Y-%m-%d')}"
    updated = update_spec_status(content, new_status, metadata)
    spec.write_text(updated, encoding="utf-8")


async def auto_design_task(task_id: str) -> str:
    """Core logic: auto-design a pending task. Returns a status message."""
    from orchestrator.tools.task_utils import git_commit_files

    # 1. Find task directory
    task_dir = _find_task_dir(task_id)
    if not task_dir:
        return f"Task {task_id} not found in current/"

    # 2. Check status is pending
    status = _read_spec_status(task_dir)
    if status != "pending":
        return f"Task {task_id} status is '{status}', not 'pending' — skipping"

    # 3. Check design.md doesn't already exist (duplicate prevention)
    if (task_dir / "design.md").exists():
        return f"Task {task_id} already has design.md — skipping"

    # 4. Run designer sub-agent
    try:
        options = create_designer_options()
        prompt = build_designer_prompt(task_dir)

        design_content = await asyncio.wait_for(
            query_agent(options, prompt), timeout=DESIGN_TIMEOUT
        )
    except TimeoutError:
        logger.warning("Designer timed out for %s", task_id)
        return f"Designer timed out for {task_id} — will retry next cycle"
    except Exception as e:
        logger.exception("Designer failed for %s", task_id)
        return f"Designer failed for {task_id}: {e}"

    if not design_content or design_content == "(no response)":
        return f"Designer produced no output for {task_id}"

    # 5. Write design.md
    (task_dir / "design.md").write_text(design_content, encoding="utf-8")

    # 6. Update status → design
    _update_spec_status(task_dir, "design")

    # 7. Commit
    if await git_commit_files(
        [str(task_dir)], f"chore(auto): {task_id} 자동 설계 — status: design"
    ):
        return f"⚠️ {task_id} design written but git push failed"

    # 8. Auto-approve evaluation
    approved, reason = can_auto_approve(design_content)
    if approved:
        _update_spec_status(task_dir, "approved")
        if await git_commit_files([str(task_dir)], f"chore(auto): {task_id} 자동 승인 — {reason}"):
            return f"⚠️ {task_id} approved locally but git push failed"
        return f"✅ {task_id} auto-designed and auto-approved: {reason}"

    logger.info("Auto-approve rejected for %s: %s", task_id, reason)
    return f"📝 {task_id} designed but not auto-approved: {reason}"


@tool(
    "run_auto_design",
    "Generate design.md for a pending task using the Designer sub-agent",
    {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
)
async def run_auto_design(args: dict) -> dict:
    """MCP tool: auto-design a pending task."""
    message = await auto_design_task(args["task_id"])
    return {"content": [{"type": "text", "text": message}]}
