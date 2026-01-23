"""Avatar generation and management for Shorts Producer Backend."""

from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path

import httpx

logger = logging.getLogger("backend")


def avatar_filename(avatar_key: str) -> str:
    """Generate a unique filename for an avatar based on its key.

    Args:
        avatar_key: The avatar key (e.g., channel name)

    Returns:
        A unique filename like 'avatar_abc123def456.png'
    """
    safe_name = avatar_key.strip() or "avatar"
    hash_value = hashlib.sha1(safe_name.encode("utf-8")).hexdigest()[:12]
    return f"avatar_{hash_value}.png"


async def ensure_avatar_file(
    avatar_key: str,
    avatar_dir: Path,
    sd_txt2img_url: str,
    timeout: float = 60.0,
) -> str | None:
    """Ensure an avatar file exists, generating it if necessary.

    Args:
        avatar_key: The avatar key to generate for
        avatar_dir: Directory to store avatar files
        sd_txt2img_url: Stable Diffusion txt2img API URL
        timeout: Request timeout in seconds

    Returns:
        The avatar filename if successful, None otherwise
    """
    filename = avatar_filename(avatar_key)
    target = avatar_dir / filename
    if target.exists():
        return filename

    prompt = (
        "anime avatar portrait, clean background, head and shoulders, "
        "soft lighting, centered, high quality"
    )
    payload = {
        "prompt": prompt,
        "negative_prompt": "verybadimagenegative_v1.3",
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
        "width": 256,
        "height": 256,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(sd_txt2img_url, json=payload, timeout=timeout)
            res.raise_for_status()
            data = res.json()
        image_b64 = (data.get("images") or [None])[0]
        if not image_b64:
            return None
        image_bytes = base64.b64decode(image_b64)
        target.write_bytes(image_bytes)
        return filename
    except Exception:
        logger.exception("Avatar generation failed")
        return None
