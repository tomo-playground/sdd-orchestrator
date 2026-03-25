"""ComfyUI async workflow runner — queue + adaptive poll + download."""

from __future__ import annotations

import asyncio
import logging

import httpx

from config import COMFYUI_EXECUTION_TIMEOUT, COMFYUI_QUEUE_TIMEOUT

logger = logging.getLogger(__name__)

# Retry settings for queue_prompt
_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]

# Adaptive polling settings
_POLL_INITIAL = 0.5
_POLL_MULTIPLIER = 1.5
_POLL_MAX = 5.0


async def queue_prompt(client: httpx.AsyncClient, workflow: dict) -> str:
    """Queue a workflow prompt on ComfyUI with exponential backoff retry.

    Args:
        client: Shared httpx async client.
        workflow: Workflow dict (after variable injection).

    Returns:
        prompt_id from ComfyUI.

    Raises:
        RuntimeError: ComfyUI returned an error response.
        httpx.ConnectError: ComfyUI server is down (no retry).
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.post("/prompt", json={"prompt": workflow})
            data = resp.json()

            if "error" in data:
                raise RuntimeError(f"ComfyUI queue error: {data['error']}")

            prompt_id = data.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI returned no prompt_id: {data}")

            return prompt_id

        except httpx.ConnectError:
            raise  # Server down — no retry
        except RuntimeError:
            raise  # Application error — no retry
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_DELAYS[attempt]
                logger.warning("queue_prompt attempt %d failed: %s, retrying in %.1fs", attempt + 1, e, delay)
                await asyncio.sleep(delay)

    raise RuntimeError(f"queue_prompt failed after {_MAX_RETRIES} attempts: {last_exc}")


async def wait_for_result(
    client: httpx.AsyncClient,
    prompt_id: str,
    output_node: str,
) -> list[bytes]:
    """Poll /history until result is ready, then download images.

    Uses adaptive polling: starts at 0.5s, increases by 1.5x, max 5s.

    Args:
        client: Shared httpx async client.
        prompt_id: From queue_prompt().
        output_node: Node ID to collect outputs from.

    Returns:
        List of image bytes.

    Raises:
        RuntimeError: Execution error from ComfyUI.
        TimeoutError: Exceeded COMFYUI_QUEUE_TIMEOUT.
    """
    poll_interval = _POLL_INITIAL
    elapsed = 0.0
    timeout = COMFYUI_QUEUE_TIMEOUT

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        try:
            resp = await client.get(f"/history/{prompt_id}")
            if resp.status_code != 200:
                poll_interval = min(poll_interval * _POLL_MULTIPLIER, _POLL_MAX)
                continue

            history = resp.json()
            if prompt_id not in history:
                poll_interval = min(poll_interval * _POLL_MULTIPLIER, _POLL_MAX)
                continue

            entry = history[prompt_id]
            status = entry.get("status", {})

            if status.get("status_str") == "error":
                node_errors = entry.get("node_errors", {})
                raise RuntimeError(f"ComfyUI execution error: {status}. Node errors: {node_errors}")

            outputs = entry.get("outputs", {})
            if output_node not in outputs:
                poll_interval = min(poll_interval * _POLL_MULTIPLIER, _POLL_MAX)
                continue

            # Download images
            images: list[bytes] = []
            for img in outputs[output_node].get("images", []):
                # Let httpx handle URL encoding via params dict (no manual quoting)
                img_resp = await client.get(
                    "/view",
                    params={
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                    },
                    timeout=COMFYUI_EXECUTION_TIMEOUT,
                )
                img_resp.raise_for_status()
                images.append(img_resp.content)

            logger.info("Received %d image(s) from prompt %s (%.1fs)", len(images), prompt_id, elapsed)
            return images

        except (httpx.HTTPError, RuntimeError, TimeoutError):
            raise
        except Exception as e:
            logger.warning("Poll error (will retry): %s", e, exc_info=True)
            poll_interval = min(poll_interval * _POLL_MULTIPLIER, _POLL_MAX)

    raise TimeoutError(f"ComfyUI execution timeout ({timeout}s) for prompt {prompt_id}")


async def run_workflow(
    client: httpx.AsyncClient,
    workflow: dict,
    output_node: str,
) -> list[bytes]:
    """Queue workflow and wait for result images.

    Args:
        client: Shared httpx async client.
        workflow: Ready-to-execute workflow (variables already injected).
        output_node: Node ID for output collection.

    Returns:
        List of image bytes.
    """
    prompt_id = await queue_prompt(client, workflow)
    logger.info("Queued workflow (prompt_id=%s)", prompt_id)
    return await wait_for_result(client, prompt_id, output_node)
