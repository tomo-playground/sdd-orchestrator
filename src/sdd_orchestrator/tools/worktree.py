"""Worktree management tools — launch and monitor /sdd-run processes."""

from __future__ import annotations

import asyncio
import json
import logging

from claude_agent_sdk import tool

from sdd_orchestrator.config import MAX_PARALLEL_RUNS

logger = logging.getLogger(__name__)

# Module-level reference to the shared StateStore, set by set_state_store()
_state_store = None
# Background tasks watching processes (prevent GC)
_watch_tasks: set[asyncio.Task] = set()


def set_state_store(store) -> None:
    """Inject the shared StateStore instance (called from main.py)."""
    global _state_store
    _state_store = store


async def _watch_process(proc: asyncio.subprocess.Process, task_id: str, run_id: int) -> None:
    """Background task: wait for process exit and update state."""
    try:
        exit_code = await proc.wait()
        logger.info("Worktree %s finished (exit_code=%d, run_id=%d)", task_id, exit_code, run_id)
        if _state_store:
            _state_store.finish_run(run_id, exit_code)
        # PR 있으면 running 유지, 없으면 approved 복원
        if _has_open_pr(task_id):
            logger.info("%s finished (exit=%d) with open PR — keeping running", task_id, exit_code)
        elif exit_code != 0 and _state_store:
            _state_store.set_task_status(task_id, "approved")
        elif exit_code == 0 and _state_store:
            # 성공 종료 + PR 없음 (드문 케이스) → approved로 복원하여 재시도 방지
            _state_store.set_task_status(task_id, "approved")
            logger.info("%s succeeded without PR — restored to approved", task_id)
    except Exception:
        logger.exception("Error watching worktree process %s", task_id)
        if _state_store:
            _state_store.finish_run(run_id, exit_code=1)
        if not _has_open_pr(task_id) and _state_store:
            _state_store.set_task_status(task_id, "approved")


async def do_launch_sdd_run(task_id: str) -> dict:
    """Core logic: launch claude --worktree for /sdd-run."""
    if not _state_store:
        return _error("State store not initialized")

    # Check parallel limit
    running = _state_store.get_running_runs()
    if len(running) >= MAX_PARALLEL_RUNS:
        return _error(
            f"Parallel limit reached ({len(running)}/{MAX_PARALLEL_RUNS}). "
            f"Running: {[r['task_id'] for r in running]}"
        )

    # Check if already running
    for r in running:
        if r["task_id"] == task_id:
            return _error(f"{task_id} is already running (run_id={r['id']})")

    # Check consecutive failures → blocked
    failures = _state_store.get_consecutive_failures(task_id)
    if failures >= 3:
        return _error(f"{task_id} is blocked after {failures} consecutive failures")

    # Check if open PR already exists → skip (이미 코딩 완료)
    open_pr = _has_open_pr(task_id)
    if open_pr:
        _state_store.set_task_status(task_id, "running")
        return _error(f"{task_id} already has open PR ({open_pr}) — skipping launch")

    try:
        from sdd_orchestrator.config import PROJECT_ROOT

        # 기존 worktree 잔류 시: 프로세스 없으면 삭제, 있으면 스킵
        wt_dir = PROJECT_ROOT / ".claude/worktrees" / task_id
        if wt_dir.exists():
            if _is_worktree_in_use(task_id):
                return _error(f"{task_id} worktree is in use by another process — skipping launch")
            import subprocess

            subprocess.run(
                ["git", "worktree", "remove", str(wt_dir), "--force"],
                capture_output=True,
                timeout=10,
                cwd=str(PROJECT_ROOT),
            )
            subprocess.run(
                ["git", "worktree", "prune"],
                capture_output=True,
                timeout=5,
                cwd=str(PROJECT_ROOT),
            )
            logger.info("Removed stale worktree before launch: %s", task_id)

        proc = await asyncio.create_subprocess_exec(
            "claude",
            "--worktree",
            task_id,
            "--dangerously-skip-permissions",
            "-p",
            f"/sdd-run {task_id}",
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        run_id = _state_store.start_run(task_id, pid=proc.pid)

        # DB status: approved → running (재실행 방지)
        _state_store.set_task_status(task_id, "running")

        # Background watcher
        task = asyncio.create_task(_watch_process(proc, task_id, run_id))
        _watch_tasks.add(task)
        task.add_done_callback(_watch_tasks.discard)

        logger.info("Launched worktree for %s (pid=%d, run_id=%d)", task_id, proc.pid, run_id)
        return _ok(f"Launched {task_id} (pid={proc.pid}, run_id={run_id})")

    except FileNotFoundError:
        return _error("claude CLI not found")
    except Exception as e:
        return _error(f"Failed to launch: {e}")


async def do_check_running_worktrees() -> dict:
    """Core logic: list running worktree processes. Prune dead PIDs."""

    if not _state_store:
        return _error("State store not initialized")

    running = _state_store.get_running_runs()
    alive = []
    for run in running:
        pid = run.get("pid")
        if pid and _is_pid_alive(pid):
            alive.append(run)
        elif pid:
            # DB에 있지만 프로세스 없음 → stale, 정리
            _state_store.finish_run(run.get("id", 0), -1)
            # DB 복원 (오케스트레이터 재시작 시 _watch_process 콜백 소실 대비)
            # open PR이 있으면 복원하지 않음 — PR 리뷰 대기 중
            task_id = run.get("task_id", "")
            if task_id and _state_store and not _has_open_pr(task_id):
                _state_store.set_task_status(task_id, "approved")
                logger.info("Dead PID %d → status restored to approved: %s", pid, task_id)
    return {"content": [{"type": "text", "text": json.dumps(alive, ensure_ascii=False)}]}


def _has_open_pr(task_id: str) -> str | None:
    """Check if task_id has an open PR. Returns 'PR #N' or None.

    Uses exact SP-NNN matching on branch names to avoid partial matches
    (e.g. SP-117 must not match feat/SP-111-xxx).
    """
    import re
    import subprocess

    from sdd_orchestrator.tools.github import _repo_args

    try:
        r = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,headRefName",
                *_repo_args(),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None

        prs = json.loads(r.stdout)
        for pr in prs:
            branch = pr.get("headRefName", "")
            match = re.search(r"SP-\d+", branch)
            if match and match.group() == task_id:
                return f"PR #{pr['number']}"
    except Exception:
        logger.warning("Failed to check open PR for %s", task_id, exc_info=True)
    return None


def _is_worktree_in_use(task_id: str) -> bool:
    """Check if any claude process is using a worktree for this task_id."""
    import subprocess

    patterns = [f"--worktree {task_id} ", f"--worktree {task_id}$"]
    for pat in patterns:
        try:
            result = subprocess.run(
                ["pgrep", "-f", pat],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
    return False


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    import os

    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


@tool(
    "launch_sdd_run",
    "Launch a worktree to execute /sdd-run for a task",
    {
        "type": "object",
        "properties": {"task_id": {"type": "string", "description": "Task ID (e.g. SP-067)"}},
        "required": ["task_id"],
    },
)
async def launch_sdd_run(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_launch_sdd_run(args["task_id"])


@tool("check_running_worktrees", "List running worktree processes and their status", {})
async def check_running_worktrees(args: dict) -> dict:
    """MCP tool wrapper."""
    return await do_check_running_worktrees()


def _ok(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}]}


def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": f"Error: {message}"}], "isError": True}
