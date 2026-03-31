"""SDD task management MCP tools — read_task, approve_design, create_task."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path

from claude_agent_sdk import tool

from sdd_orchestrator.config import TASKS_CURRENT_DIR, TASKS_DONE_DIR
from sdd_orchestrator.tools.task_utils import (
    _error,
    _ok,
    generate_slug,
    git_commit_files,
    next_sp_number,
)

logger = logging.getLogger(__name__)

# Module-level StateStore reference, set by set_state_store()
_state_store = None


def set_state_store(store) -> None:
    """Inject the shared StateStore instance (called from main.py)."""
    global _state_store
    _state_store = store


_MAX_CONTENT_LEN = 8000
_TRUNCATION_NOTE = "\n\n[TRUNCATED — use read_task for full text]"
_TASK_ID_RE = re.compile(r"^SP-\d{3}$")


# ── Helpers ───────────────────────────────────────────────


def _find_task(
    task_id: str,
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
) -> tuple[Path | None, str]:
    """Find task directory or file. Returns (path, location) or (None, '').

    location values: 'current', 'done', 'done_legacy', '' (not found),
    'invalid' (bad task_id format), 'ambiguous' (multiple matches).
    """
    if not _TASK_ID_RE.fullmatch(task_id):
        return None, "invalid"

    # 1. current/ directory pattern
    if current_dir.exists():
        matches = sorted(current_dir.glob(f"{task_id}_*/spec.md"))
        if len(matches) > 1:
            return None, "ambiguous"
        if matches:
            return matches[0].parent, "current"

    # 2. done/ directory pattern
    if done_dir.exists():
        matches = sorted(done_dir.glob(f"{task_id}_*/spec.md"))
        if len(matches) > 1:
            return None, "ambiguous"
        if matches:
            return matches[0].parent, "done"
        # 3. done/ legacy .md file pattern
        legacy = sorted(done_dir.glob(f"{task_id}_*.md"))
        if len(legacy) > 1:
            return None, "ambiguous"
        if legacy:
            return legacy[0], "done_legacy"

    return None, ""


def _truncate(text: str) -> str:
    if len(text) <= _MAX_CONTENT_LEN:
        return text
    return text[:_MAX_CONTENT_LEN] + _TRUNCATION_NOTE


# ── read_task ─────────────────────────────────────────────


async def do_read_task(
    task_id: str,
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
) -> dict:
    """Read spec.md + design.md content for a task."""
    path, location = _find_task(task_id, current_dir, done_dir)
    if path is None:
        if location == "invalid":
            return _error(f"잘못된 태스크 ID 형식: {task_id} (SP-NNN 필요)")
        if location == "ambiguous":
            return _error(f"중복 태스크 발견: {task_id}")
        return _error(f"Task {task_id} not found")

    # Get status from state.db
    status = _state_store.get_task_status(task_id) if _state_store else "pending"

    # Legacy .md file (single file, no directory)
    if location == "done_legacy":
        content = path.read_text(encoding="utf-8")
        result = {
            "task_id": task_id,
            "status": status,
            "has_design": False,
            "directory": path.name,
            "spec": _truncate(content),
            "design": None,
        }
        return _ok(json.dumps(result, ensure_ascii=False))

    # Directory-based task
    spec_path = path / "spec.md"
    spec_content = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
    design_path = path / "design.md"
    design_content = design_path.read_text(encoding="utf-8") if design_path.exists() else None

    result = {
        "task_id": task_id,
        "status": status,
        "has_design": design_content is not None,
        "directory": path.name,
        "spec": _truncate(spec_content),
        "design": _truncate(design_content) if design_content else None,
    }
    return _ok(json.dumps(result, ensure_ascii=False))


@tool(
    "read_task",
    "Read task spec and design details",
    {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
)
async def read_task(args: dict) -> dict:
    return await do_read_task(args["task_id"])


# ── approve_design ────────────────────────────────────────


async def do_approve_design(
    task_id: str,
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
) -> dict:
    """Approve task design: update status + git commit + push."""
    path, location = _find_task(task_id, current_dir, done_dir)
    if path is None:
        if location == "invalid":
            return _error(f"잘못된 태스크 ID 형식: {task_id} (SP-NNN 필요)")
        if location == "ambiguous":
            return _error(f"중복 태스크 발견: {task_id}")
        return _error(f"Task {task_id} not found")
    if location != "current":
        return _error(f"Task {task_id}은 current/에 없습니다 (위치: {location})")

    task_dir = path
    spec_path = task_dir / "spec.md"
    design_path = task_dir / "design.md"

    # design.md must exist
    if not design_path.exists():
        return _error("설계 파일이 없습니다 (design.md)")

    # StateStore is required — status must be persisted (no spec.md fallback)
    if not _state_store:
        return _error("StateStore가 초기화되지 않았습니다")

    # Read current status from DB
    current_status = _state_store.get_task_status(task_id)

    # Only pending/design can be approved
    if current_status in ("approved", "running", "done"):
        return _error(f"이미 승인된 태스크입니다 (status: {current_status})")

    # Update status in DB
    _state_store.set_task_status(task_id, "approved")

    # Git commit + push design.md
    err = await git_commit_files(
        [str(design_path)],
        f"chore: {task_id} 설계 승인",
    )
    if err:
        # Rollback DB status
        _state_store.set_task_status(task_id, current_status)
        return _error(f"Git 커밋 실패: {err}")

    return _ok(f"{task_id} 설계 승인 완료 (status: approved)")


@tool(
    "approve_design",
    "Approve a task design (updates status to approved and commits)",
    {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
)
async def approve_design(args: dict) -> dict:
    return await do_approve_design(args["task_id"])


# ── create_task ───────────────────────────────────────────


async def do_create_task(
    title: str,
    description: str = "",
    current_dir: Path = TASKS_CURRENT_DIR,
    done_dir: Path = TASKS_DONE_DIR,
    backlog_path: Path | None = None,
) -> dict:
    """Create a new task: auto-assign SP number + directory + spec.md."""
    from sdd_orchestrator.config import BACKLOG_PATH

    if not title.strip():
        return _error("제목이 비어 있습니다")

    # StateStore is required — new tasks must have a DB status row
    if not _state_store:
        return _error("StateStore가 초기화되지 않았습니다")

    current_dir.mkdir(parents=True, exist_ok=True)

    slug = generate_slug(title)
    task_dir = None
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
        return _error("태스크 생성 충돌이 반복되어 중단했습니다. 잠시 후 다시 시도해주세요.")

    # Generate spec.md skeleton (no status line — status lives in state.db)
    desc_section = f"\n## 배경\n\n{description}\n" if description else ""
    spec_content = f"# {task_id}: {title}\n{desc_section}\n## DoD (Definition of Done)\n\n1. \n"
    spec_path = task_dir / "spec.md"
    spec_path.write_text(spec_content, encoding="utf-8")

    # Set initial status in DB
    _state_store.set_task_status(task_id, "pending")

    # Git commit + push
    err = await git_commit_files(
        [str(spec_path)],
        f"chore: {task_id} 태스크 생성",
    )
    if err:
        shutil.rmtree(task_dir, ignore_errors=True)
        _state_store.delete_task_status(task_id)
        return _error(f"Git 커밋 실패: {err}")

    result = {"task_id": task_id, "directory": dir_name, "status": "pending"}
    return _ok(json.dumps(result, ensure_ascii=False))


@tool(
    "create_task",
    "Create a new SDD task with auto-assigned SP number",
    {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Task title (Korean or English)"},
            "description": {"type": "string", "description": "Brief background/goal"},
        },
        "required": ["title"],
    },
)
async def create_task(args: dict) -> dict:
    return await do_create_task(args["title"], args.get("description", ""))
