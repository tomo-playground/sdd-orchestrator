"""Avatar generation and management for Shorts Producer Backend."""

from __future__ import annotations

import base64
import hashlib

import httpx

from config import SD_TXT2IMG_URL, logger
from services.storage import storage


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
    """Ensure an avatar file exists, using StorageService.

    Args:
        avatar_key: The avatar key to generate for
        timeout: Request timeout in seconds

    Returns:
        The storage key of the avatar if successful, None otherwise
    """
    filename = avatar_filename(avatar_key)
    storage_key = f"shared/avatars/{filename}"

    if storage.exists(storage_key):
        logger.info(f"Avatar found in storage: {storage_key}")
        return storage_key

    logger.info(f"Avatar not found, generating: {avatar_key} -> {storage_key}")
    # ... (payload and other logic remains same, but save via storage)
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
        storage.save(storage_key, image_bytes, content_type="image/png")
        logger.info(f"✅ Avatar generated successfully: {storage_key}")
        return storage_key
    except httpx.ConnectError:
        logger.warning("SD WebUI not running, generating simple avatar instead")
        try:
            from services.simple_avatar import generate_simple_avatar

            # Simple avatar currently writes to path, we might need to adapt it
            # or just use a temporary file.
            fake_path = storage.get_local_path(storage_key)
            fake_path.parent.mkdir(parents=True, exist_ok=True)
            generate_simple_avatar(avatar_key, fake_path)

            if storage_key.startswith("shared/"): # Trigger sync if needed for S3
                 storage.save(storage_key, fake_path.read_bytes(), content_type="image/png")

            logger.info(f"✅ Simple avatar generated: {storage_key}")
            return storage_key
        except Exception as e2:
            logger.exception(f"Simple avatar generation failed: {e2}")
            return None
    except Exception as e:
        logger.exception(f"Avatar generation failed: {e}")
        return None
