"""Avatar generation and management for Shorts Producer Backend."""

from __future__ import annotations

import base64
import hashlib

import httpx

from config import SD_TXT2IMG_URL, logger
from services.storage import get_storage


def avatar_filename(avatar_key: str) -> str:
    """Generate a unique filename for an avatar based on its key.

    Args:
        avatar_key: The avatar key (e.g., channel name or URL)

    Returns:
        A unique filename like 'avatar_abc123def456.png'
    """
    safe_name = avatar_key.strip() or "avatar"
    hash_value = hashlib.sha256(safe_name.encode("utf-8")).hexdigest()[:12]
    return f"avatar_{hash_value}.png"


async def _download_avatar_from_url(url: str, timeout: float = 60.0) -> str | None:
    """Download avatar image from a URL and save to storage.

    Args:
        url: The URL to download the avatar from
        timeout: Request timeout in seconds

    Returns:
        The storage key if successful, None otherwise
    """
    filename = avatar_filename(url)
    storage_key = f"shared/avatars/{filename}"
    storage = get_storage()

    if storage.exists(storage_key):
        logger.info(f"Avatar (from URL) found in storage: {storage_key}")
        return storage_key

    logger.info(f"Downloading avatar from URL: {url}")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=timeout, follow_redirects=True)
            res.raise_for_status()
            image_bytes = res.content
            if len(image_bytes) < 100:
                logger.warning(f"Downloaded avatar too small ({len(image_bytes)} bytes)")
                return None
            storage.save(storage_key, image_bytes, content_type="image/png")
            logger.info(f"✅ Avatar downloaded from URL: {storage_key}")
            return storage_key
    except Exception as e:
        logger.exception(f"Failed to download avatar from URL: {e}")
        return None


async def ensure_avatar_file(
    avatar_key: str,
    timeout: float = 60.0,
) -> str | None:
    """Ensure an avatar file exists, using StorageService.

    # INTENTIONAL BYPASS: This function does NOT use generate_image_with_v3()
    # because avatars are generic placeholder images (256x256) with a fixed
    # prompt, unrelated to any character/storyboard/style profile pipeline.

    Args:
        avatar_key: The avatar key (can be a URL, storage key, or simple string)
        timeout: Request timeout in seconds

    Returns:
        The storage key of the avatar if successful, None otherwise
    """
    storage = get_storage()

    # If avatar_key is a URL, download it directly
    if avatar_key.startswith(("http://", "https://")):
        return await _download_avatar_from_url(avatar_key, timeout)

    # If avatar_key is already an existing storage key (e.g., characters/9/preview/...)
    if storage.exists(avatar_key):
        logger.info(f"Avatar key is existing storage key: {avatar_key}")
        return avatar_key

    filename = avatar_filename(avatar_key)
    storage_key = f"shared/avatars/{filename}"

    if storage.exists(storage_key):
        logger.info(f"Avatar found in storage: {storage_key}")
        return storage_key

    logger.info(f"Avatar not found, generating: {avatar_key} -> {storage_key}")
    prompt = "anime avatar portrait, clean background, head and shoulders, soft lighting, centered, high quality"
    payload = {
        "prompt": prompt,
        "negative_prompt": "verybadimagenegative_v1.3",
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M",
        "scheduler": "karras",
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
        get_storage().save(storage_key, image_bytes, content_type="image/png")
        logger.info(f"✅ Avatar generated successfully: {storage_key}")
        return storage_key
    except httpx.ConnectError:
        logger.warning("SD WebUI not running, generating simple avatar instead")
        try:
            from services.simple_avatar import generate_simple_avatar

            storage = get_storage()
            fake_path = storage.get_local_path(storage_key)
            fake_path.parent.mkdir(parents=True, exist_ok=True)
            generate_simple_avatar(avatar_key, fake_path)

            if storage_key.startswith("shared/"):
                get_storage().save(storage_key, fake_path.read_bytes(), content_type="image/png")

            logger.info(f"✅ Simple avatar generated: {storage_key}")
            return storage_key
        except Exception as e2:
            logger.exception(f"Simple avatar generation failed: {e2}")
            return None
    except Exception as e:
        logger.exception(f"Avatar generation failed: {e}")
        return None
