"""Worktree management tools — launch and monitor /sdd-run processes."""

from __future__ import annotations

import asyncio
import json
import logging

from claude_agent_sdk import tool

from orchestrator.config import MAX_PARALLEL_RUNS

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
    except Exception:
        logger.exception("Error watching worktree process %s", task_id)
        if _state_store:
            _state_store.finish_run(run_id, exit_code=1)


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

    try:
        proc = await asyncio.create_subprocess_exec(
            "claude",
            "--worktree",
            task_id,
            "--dangerously-skip-permissions",
            "-p",
            f"/sdd-run {task_id}",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        run_id = _state_store.start_run(task_id, pid=proc.pid)

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
    """Core logic: list running worktree processes."""
    if not _state_store:
        return _error("State store not initialized")

    running = _state_store.get_running_runs()
    return {"content": [{"type": "text", "text": json.dumps(running, ensure_ascii=False)}]}


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
