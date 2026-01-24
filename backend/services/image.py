"""Image utility functions for Shorts Producer Backend."""

from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import urlparse

from config import OUTPUT_DIR


def decode_data_url(data_url: str) -> bytes:
    """Decode a base64 data URL to bytes."""
    if not data_url:
        raise ValueError("Empty image data")
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


def load_image_bytes(source: str) -> bytes:
    """Load image bytes from various sources (data URL, HTTP URL, local path, or raw base64).

    Args:
        source: Data URL, HTTP URL, local path starting with /outputs/, or raw base64

    Returns:
        Image bytes

    Raises:
        ValueError: If source is empty, invalid, or unsupported
    """
    if not source:
        raise ValueError("Empty image data")
    if source.startswith("data:"):
        return decode_data_url(source)
    if source.startswith(("http://", "https://")):
        parsed = urlparse(source)
        path = parsed.path
    else:
        path = source
    if path.startswith("/outputs/"):
        rel_path = path.replace("/outputs/", "", 1)
        candidate = (OUTPUT_DIR / rel_path).resolve()
        if OUTPUT_DIR.resolve() not in candidate.parents and candidate != OUTPUT_DIR.resolve():
            raise ValueError("Invalid image path")
        return candidate.read_bytes()
    # Try raw base64 as fallback
    try:
        return base64.b64decode(source)
    except Exception:
        raise ValueError("Unsupported image source")
