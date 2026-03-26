"""SD Client factory — singleton access to the ComfyUI backend client."""

from __future__ import annotations

from services.sd_client import SDClientBase

_client: SDClientBase | None = None


def get_sd_client() -> SDClientBase:
    """Return the singleton ComfyUI client."""
    global _client  # noqa: PLW0603
    if _client is None:
        from services.sd_client.comfyui import ComfyUIClient

        _client = ComfyUIClient()
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
