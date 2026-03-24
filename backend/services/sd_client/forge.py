"""Forge (SD WebUI) client implementation."""

from __future__ import annotations

import json

import httpx

from config import (
    CONTROLNET_API_TIMEOUT,
    CONTROLNET_DETECT_TIMEOUT,
    SD_API_TIMEOUT,
    SD_BASE_URL,
    SD_MODEL_SWITCH_TIMEOUT,
    SD_PROGRESS_POLL_TIMEOUT,
    SD_TIMEOUT_SECONDS,
    logger,
)
from services.sd_client import SDClientBase
from services.sd_client.types import SDProgressResult, SDTxt2ImgResult


class ForgeClient(SDClientBase):
    """SD WebUI / Forge backend client.

    Uses a shared httpx.AsyncClient for connection reuse.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self._base_url = (base_url or SD_BASE_URL).rstrip("/")
        self._timeout = timeout or SD_TIMEOUT_SECONDS
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return shared httpx client, creating lazily."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self._base_url)
        return self._client

    async def close(self) -> None:
        """Close the shared httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult:
        """Generate image from text prompt via Forge /sdapi/v1/txt2img."""
        t = timeout or self._timeout
        client = self._get_client()
        resp = await client.post("/sdapi/v1/txt2img", json=payload, timeout=t)
        resp.raise_for_status()
        data = resp.json()

        info_raw = data.get("info", "{}")
        info = json.loads(info_raw) if isinstance(info_raw, str) else info_raw
        if not isinstance(info, dict):
            info = {}
        seed = info.get("seed")

        return SDTxt2ImgResult(
            images=data.get("images", []),
            info=info,
            seed=int(seed) if seed is not None else None,
        )

    async def get_options(self) -> dict:
        """Get SD WebUI options."""
        client = self._get_client()
        resp = await client.get("/sdapi/v1/options", timeout=SD_API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    async def set_options(self, options: dict, timeout: float | None = None) -> dict:
        """Set SD WebUI options (e.g. switch checkpoint)."""
        t = timeout or SD_MODEL_SWITCH_TIMEOUT
        client = self._get_client()
        resp = await client.post("/sdapi/v1/options", json=options, timeout=t)
        resp.raise_for_status()
        return resp.json()

    async def get_models(self) -> list[dict]:
        """List available SD models."""
        client = self._get_client()
        resp = await client.get("/sdapi/v1/sd-models", timeout=SD_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    async def get_loras(self) -> list[dict]:
        """List available LoRAs."""
        client = self._get_client()
        resp = await client.get("/sdapi/v1/loras", timeout=SD_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    async def get_progress(self) -> SDProgressResult:
        """Get current generation progress."""
        client = self._get_client()
        resp = await client.get("/sdapi/v1/progress", timeout=SD_PROGRESS_POLL_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return SDProgressResult(
            progress=data.get("progress", 0.0),
            textinfo=data.get("textinfo", ""),
            current_image=data.get("current_image"),
        )

    async def controlnet_detect(self, payload: dict) -> dict:
        """Run ControlNet detection (e.g., OpenPose)."""
        client = self._get_client()
        resp = await client.post("/controlnet/detect", json=payload, timeout=CONTROLNET_DETECT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    async def check_controlnet(self) -> bool:
        """Check if ControlNet extension is available."""
        client = self._get_client()
        for endpoint in ("/controlnet/version", "/controlnet/model_list"):
            try:
                resp = await client.get(endpoint, timeout=CONTROLNET_API_TIMEOUT)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
        return False

    async def get_controlnet_models(self) -> list[str]:
        """List available ControlNet models."""
        client = self._get_client()
        try:
            resp = await client.get("/controlnet/model_list", timeout=CONTROLNET_API_TIMEOUT)
            if resp.status_code == 200:
                return resp.json().get("model_list", [])
        except Exception as e:
            logger.warning("Failed to get ControlNet models: %s", e)
        return []
