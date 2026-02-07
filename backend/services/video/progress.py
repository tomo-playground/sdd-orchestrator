"""Render task progress tracking for SSE streaming.

In-memory task store for single-user local app.
Tasks auto-expire after RENDER_TASK_TTL_SECONDS.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from config import logger

# Lazy import to avoid circular dependency at module level
_RENDER_TASK_TTL_SECONDS: int | None = None


def _get_ttl() -> int:
    global _RENDER_TASK_TTL_SECONDS
    if _RENDER_TASK_TTL_SECONDS is None:
        from config import RENDER_TASK_TTL_SECONDS

        _RENDER_TASK_TTL_SECONDS = RENDER_TASK_TTL_SECONDS
    return _RENDER_TASK_TTL_SECONDS


class RenderStage(str, Enum):
    QUEUED = "queued"
    SETUP_AVATARS = "setup_avatars"
    PROCESS_SCENES = "process_scenes"
    CALCULATE_DURATIONS = "calculate_durations"
    PREPARE_BGM = "prepare_bgm"
    BUILD_FILTERS = "build_filters"
    ENCODE = "encode"
    UPLOAD = "upload"
    COMPLETED = "completed"
    FAILED = "failed"


# Stage weight ranges for overall percent calculation
_STAGE_RANGES: dict[RenderStage, tuple[int, int]] = {
    RenderStage.QUEUED: (0, 0),
    RenderStage.SETUP_AVATARS: (0, 2),
    RenderStage.PROCESS_SCENES: (2, 52),
    RenderStage.CALCULATE_DURATIONS: (52, 53),
    RenderStage.PREPARE_BGM: (53, 63),
    RenderStage.BUILD_FILTERS: (63, 65),
    RenderStage.ENCODE: (65, 95),
    RenderStage.UPLOAD: (95, 100),
    RenderStage.COMPLETED: (100, 100),
    RenderStage.FAILED: (0, 0),
}


@dataclass
class TaskProgress:
    task_id: str
    stage: RenderStage = RenderStage.QUEUED
    percent: int = 0
    stage_detail: str = ""
    encode_percent: int = 0
    total_scenes: int = 0
    current_scene: int = 0
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    _version: int = field(default=0)
    _event: asyncio.Event = field(default_factory=asyncio.Event)

    def notify(self) -> None:
        """Wake up SSE consumers. Uses version counter to avoid TOCTOU race."""
        self._version += 1
        self._event.set()

    async def wait_for_update(self, known_version: int, timeout: float = 15.0) -> bool:
        """Wait until version changes or timeout. Returns True if updated."""
        if self._version != known_version:
            return True
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except TimeoutError:
            return self._version != known_version
        # Reset event for next wait cycle; safe because version is the
        # real synchronization mechanism (consumers always re-check version).
        self._event.clear()
        return self._version != known_version


# In-memory task store
_tasks: dict[str, TaskProgress] = {}


def create_task(total_scenes: int) -> TaskProgress:
    """Create a new render task and return it."""
    _cleanup_expired()
    task_id = uuid.uuid4().hex[:12]
    task = TaskProgress(task_id=task_id, total_scenes=total_scenes)
    _tasks[task_id] = task
    logger.info("[Progress] Task created: %s (%d scenes)", task_id, total_scenes)
    return task


def get_task(task_id: str) -> TaskProgress | None:
    """Get a task by ID, or None if not found / expired."""
    task = _tasks.get(task_id)
    if task and (time.time() - task.created_at) > _get_ttl():
        del _tasks[task_id]
        return None
    return task


def calc_overall_percent(task: TaskProgress) -> int:
    """Calculate overall percent from stage + sub-progress."""
    lo, hi = _STAGE_RANGES.get(task.stage, (0, 0))
    span = hi - lo

    if task.stage == RenderStage.PROCESS_SCENES and task.total_scenes > 0:
        scene_frac = (task.current_scene - 1) / task.total_scenes
        return lo + int(span * scene_frac)

    if task.stage == RenderStage.ENCODE and task.encode_percent > 0:
        return lo + int(span * task.encode_percent / 100)

    return lo


def _cleanup_expired() -> None:
    """Remove tasks older than TTL."""
    ttl = _get_ttl()
    now = time.time()
    expired = [tid for tid, t in _tasks.items() if (now - t.created_at) > ttl]
    for tid in expired:
        del _tasks[tid]
    if expired:
        logger.debug("[Progress] Cleaned up %d expired tasks", len(expired))
