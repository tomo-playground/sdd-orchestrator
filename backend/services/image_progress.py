"""Image generation task progress tracking for SSE streaming.

In-memory task store (mirrors video/progress.py pattern).
Tasks auto-expire after TTL.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from config import logger

# Task TTL (shorter than render — image gen is fast)
IMAGE_TASK_TTL_SECONDS = 600  # 10 minutes


class ImageGenStage(str, Enum):
    QUEUED = "queued"
    COMPOSING = "composing"  # Prompt composition
    GENERATING = "generating"  # SD WebUI txt2img
    STORING = "storing"  # Saving to storage
    COMPLETED = "completed"
    FAILED = "failed"


# Stage → (percent_lo, percent_hi)
_STAGE_RANGES: dict[ImageGenStage, tuple[int, int]] = {
    ImageGenStage.QUEUED: (0, 0),
    ImageGenStage.COMPOSING: (0, 10),
    ImageGenStage.GENERATING: (10, 85),
    ImageGenStage.STORING: (85, 100),
    ImageGenStage.COMPLETED: (100, 100),
    ImageGenStage.FAILED: (0, 0),
}


@dataclass
class ImageTaskProgress:
    task_id: str
    stage: ImageGenStage = ImageGenStage.QUEUED
    percent: int = 0
    message: str = ""
    sd_progress: float = 0.0  # 0.0 ~ 1.0 from SD WebUI
    preview_image: str | None = None  # Base64 preview from SD WebUI /progress
    cancelled: bool = False
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    _version: int = field(default=0)
    _event: asyncio.Event = field(default_factory=asyncio.Event)

    def notify(self) -> None:
        """Wake up SSE consumers."""
        self._version += 1
        self._event.set()

    async def wait_for_update(self, known_version: int, timeout: float = 10.0) -> bool:
        """Wait until version changes or timeout."""
        if self._version != known_version:
            return True
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except TimeoutError:
            return self._version != known_version
        self._event.clear()
        return self._version != known_version


# In-memory store
_tasks: dict[str, ImageTaskProgress] = {}


def create_image_task() -> ImageTaskProgress:
    """Create a new image generation task."""
    _cleanup_expired()
    task_id = f"img_{uuid.uuid4().hex[:10]}"
    task = ImageTaskProgress(task_id=task_id)
    _tasks[task_id] = task
    logger.info("[ImageProgress] Task created: %s", task_id)
    return task


def get_image_task(task_id: str) -> ImageTaskProgress | None:
    """Get a task by ID, or None if not found / expired."""
    task = _tasks.get(task_id)
    if task and (time.time() - task.created_at) > IMAGE_TASK_TTL_SECONDS:
        del _tasks[task_id]
        return None
    return task


def calc_percent(task: ImageTaskProgress) -> int:
    """Calculate overall percent from stage + SD progress."""
    lo, hi = _STAGE_RANGES.get(task.stage, (0, 0))
    span = hi - lo
    if task.stage == ImageGenStage.GENERATING and task.sd_progress > 0:
        return lo + int(span * task.sd_progress)
    return lo


def _cleanup_expired() -> None:
    """Remove tasks older than TTL."""
    now = time.time()
    expired = [tid for tid, t in _tasks.items() if (now - t.created_at) > IMAGE_TASK_TTL_SECONDS]
    for tid in expired:
        del _tasks[tid]
    if expired:
        logger.debug("[ImageProgress] Cleaned up %d expired tasks", len(expired))
