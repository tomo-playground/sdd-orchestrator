"""Avatar generation and management for Shorts Producer Backend."""

from __future__ import annotations

import base64
import hashlib

import httpx

from config import AVATAR_DIR, SD_TXT2IMG_URL, logger


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
    timeout: float = 60.0,
) -> str | None:
    """Ensure an avatar file exists, generating it if necessary.

    Args:
        avatar_key: The avatar key to generate for
        timeout: Request timeout in seconds

    Returns:
        The avatar filename if successful, None otherwise
    """
    # Ensure avatar directory exists
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    filename = avatar_filename(avatar_key)
    target = AVATAR_DIR / filename

    if target.exists():
        logger.info(f"Avatar found: {filename}")
        return filename

    logger.info(f"Avatar not found, generating: {avatar_key} -> {filename}")

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
        logger.info(f"Requesting avatar from SD WebUI: {SD_TXT2IMG_URL}")
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=timeout)
            res.raise_for_status()
            data = res.json()
        image_b64 = (data.get("images") or [None])[0]
        if not image_b64:
            logger.warning("SD WebUI returned no images")
            return None
        image_bytes = base64.b64decode(image_b64)
        target.write_bytes(image_bytes)
        logger.info(f"✅ Avatar generated successfully: {filename}")
        return filename
    except httpx.ConnectError:
        logger.warning("SD WebUI not running, generating simple avatar instead")
        try:
            from services.simple_avatar import generate_simple_avatar
            generate_simple_avatar(avatar_key, target)
            logger.info(f"✅ Simple avatar generated: {filename}")
            return filename
        except Exception as e2:
            logger.exception(f"Simple avatar generation failed: {e2}")
            return None
    except Exception as e:
        logger.exception(f"Avatar generation failed: {e}")
        return None
