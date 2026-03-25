"""SD Client factory — singleton access to the active SD backend client."""

from __future__ import annotations

from config import SD_CLIENT_TYPE
from services.sd_client import SDClientBase

_client: SDClientBase | None = None


def get_sd_client() -> SDClientBase:
    """Return the singleton SD client for the configured backend type."""
    global _client  # noqa: PLW0603
    if _client is None:
        if SD_CLIENT_TYPE == "forge":
            from services.sd_client.forge import ForgeClient

            _client = ForgeClient()
        elif SD_CLIENT_TYPE == "comfy":
            from services.sd_client.comfyui import ComfyUIClient

            _client = ComfyUIClient()
        else:
            raise ValueError(f"Unknown SD_CLIENT_TYPE: {SD_CLIENT_TYPE!r}")
    return _client


async def close_sd_client() -> None:
    """Close the singleton SD client (call from lifespan shutdown)."""
    global _client  # noqa: PLW0603
    if _client is not None:
        try:
            await _client.close()
        finally:
            _client = None


def reset_sd_client() -> None:
    """Reset the singleton (for testing)."""
    global _client  # noqa: PLW0603
    _client = None
