"""SD WebUI /sdapi/v1/progress polling for image generation tasks."""

from __future__ import annotations

import asyncio

import httpx

from config import SD_BASE_URL, logger
from services.image_progress import ImageGenStage, ImageTaskProgress, calc_percent

SD_PROGRESS_URL = f"{SD_BASE_URL}/sdapi/v1/progress"
POLL_INTERVAL_SECONDS = 1.5


async def poll_sd_progress(task: ImageTaskProgress) -> None:
    """Poll SD WebUI progress endpoint and update task until generation finishes.

    Runs as an asyncio background coroutine while the main generate_scene_image
    call is in progress. Stops when task.stage leaves GENERATING.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        while task.stage == ImageGenStage.GENERATING:
            try:
                resp = await client.get(SD_PROGRESS_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    progress = data.get("progress", 0.0)
                    task.sd_progress = min(progress, 0.99)
                    task.percent = calc_percent(task)
                    eta_text = data.get("textinfo", "")
                    if eta_text:
                        task.stage_detail = eta_text
                    task.notify()
            except Exception:
                logger.debug("[SD Poll] Progress fetch failed (SD WebUI may be busy)")

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
