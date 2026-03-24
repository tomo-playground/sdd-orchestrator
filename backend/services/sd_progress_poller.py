"""SD WebUI /sdapi/v1/progress polling for image generation tasks."""

from __future__ import annotations

import asyncio

from config import logger
from services.image_progress import ImageGenStage, ImageTaskProgress, calc_percent
from services.sd_client.factory import get_sd_client

POLL_INTERVAL_SECONDS = 1.5


async def poll_sd_progress(task: ImageTaskProgress) -> None:
    """Poll SD WebUI progress endpoint and update task until generation finishes.

    Runs as an asyncio background coroutine while the main generate_scene_image
    call is in progress. Stops when task.stage leaves GENERATING or task is cancelled.
    """
    sd = get_sd_client()
    while task.stage == ImageGenStage.GENERATING and not task.cancelled:
        try:
            result = await sd.get_progress()
            task.sd_progress = min(result.progress, 0.99)
            task.percent = calc_percent(task)
            if result.textinfo:
                task.message = result.textinfo
            if result.current_image:
                task.preview_image = result.current_image
            task.notify()
        except Exception:
            logger.debug("[SD Poll] Progress fetch failed (SD WebUI may be busy)")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
