"""SD Client abstraction layer.

Provides a unified interface for Stable Diffusion backends (Forge, ComfyUI).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from services.sd_client.types import SDProgressResult, SDTxt2ImgResult

__all__ = ["SDClientBase", "SDProgressResult", "SDTxt2ImgResult", "get_sd_client", "reset_sd_client"]


def get_sd_client() -> SDClientBase:
    """Convenience re-export from factory."""
    from services.sd_client.factory import get_sd_client as _get

    return _get()


def reset_sd_client() -> None:
    """Convenience re-export from factory."""
    from services.sd_client.factory import reset_sd_client as _reset

    _reset()


class SDClientBase(ABC):
    """Abstract base class for SD backend clients."""

    @abstractmethod
    async def txt2img(self, payload: dict, timeout: float | None = None) -> SDTxt2ImgResult:
        """Generate image from text prompt."""

    @abstractmethod
    async def get_options(self) -> dict:
        """Get current SD options (checkpoint, etc.)."""

    @abstractmethod
    async def set_options(self, options: dict, timeout: float | None = None) -> dict:
        """Set SD options (switch checkpoint, etc.)."""

    @abstractmethod
    async def get_models(self) -> list[dict]:
        """List available SD models."""

    @abstractmethod
    async def get_loras(self) -> list[dict]:
        """List available LoRAs."""

    @abstractmethod
    async def get_progress(self) -> SDProgressResult:
        """Get current generation progress."""

    @abstractmethod
    async def controlnet_detect(self, payload: dict) -> dict:
        """Run ControlNet detection (e.g., OpenPose)."""

    @abstractmethod
    async def check_controlnet(self) -> bool:
        """Check if ControlNet extension is available."""

    @abstractmethod
    async def get_controlnet_models(self) -> list[str]:
        """List available ControlNet models."""
