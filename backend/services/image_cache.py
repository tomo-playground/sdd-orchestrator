"""Image Generation Cache — filesystem-based cache for SD API results.

Design mirrors the TTS cache pattern (file-based, hash key, LRU eviction).
Only caches deterministic results (seed != -1).

Cache key: sha256(prompt + negative + seed + w/h + steps + cfg + sampler + clip_skip
           + controlnet_fingerprint)[:16]
"""

from __future__ import annotations

import hashlib
import json

from config import (
    SD_DEFAULT_CFG_SCALE,
    SD_DEFAULT_CLIP_SKIP,
    SD_DEFAULT_HEIGHT,
    SD_DEFAULT_STEPS,
    SD_DEFAULT_WIDTH,
    SD_IMAGE_CACHE_DIR,
    SD_IMAGE_CACHE_ENABLED,
    SD_IMAGE_CACHE_MAX_SIZE_MB,
    logger,
)

_CACHE_DIR = SD_IMAGE_CACHE_DIR


def image_cache_key(payload: dict) -> str:
    """Generate a deterministic cache key from an SD generation payload."""
    key_parts = {
        "prompt": payload.get("prompt", ""),
        "negative_prompt": payload.get("negative_prompt", ""),
        "seed": payload.get("seed", -1),
        "width": payload.get("width", SD_DEFAULT_WIDTH),
        "height": payload.get("height", SD_DEFAULT_HEIGHT),
        "steps": payload.get("steps", SD_DEFAULT_STEPS),
        "cfg_scale": payload.get("cfg_scale", SD_DEFAULT_CFG_SCALE),
        "sampler_name": payload.get("sampler_name", ""),
        "scheduler": payload.get("scheduler", ""),
        "clip_skip": payload.get("override_settings", {}).get("CLIP_stop_at_last_layers", SD_DEFAULT_CLIP_SKIP),
    }
    # Include ControlNet fingerprint if present
    alwayson = payload.get("alwayson_scripts", {})
    cn_args = alwayson.get("controlnet", {}).get("args", [])
    if cn_args:
        key_parts["controlnet"] = json.dumps(
            [{"model": a.get("model", ""), "weight": a.get("weight", 1.0)} for a in cn_args if isinstance(a, dict)],
            sort_keys=True,
        )

    raw = json.dumps(key_parts, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_cached_image(key: str) -> str | None:
    """Return cached base64 image data, or None if not found."""
    if not SD_IMAGE_CACHE_ENABLED:
        return None

    path = _CACHE_DIR / f"{key}.b64"
    if path.exists():
        logger.info("🎯 [Image Cache] HIT key=%s", key)
        # Touch file for LRU ordering
        path.touch()
        return path.read_text()

    return None


def save_cached_image(key: str, image_b64: str) -> None:
    """Save a base64 image to cache. Triggers eviction if over size limit."""
    if not SD_IMAGE_CACHE_ENABLED:
        return

    path = _CACHE_DIR / f"{key}.b64"
    path.write_text(image_b64)
    logger.info("💾 [Image Cache] SAVE key=%s size=%dKB", key, len(image_b64) // 1024)

    _maybe_evict()


def clear_image_cache() -> int:
    """Delete all cached images. Returns count of deleted files."""
    count = 0
    for f in _CACHE_DIR.glob("*.b64"):
        f.unlink()
        count += 1
    logger.info("🗑️ [Image Cache] Cleared %d files", count)
    return count


def get_cache_stats() -> dict:
    """Return cache statistics."""
    files = list(_CACHE_DIR.glob("*.b64"))
    total_bytes = sum(f.stat().st_size for f in files)
    return {
        "enabled": SD_IMAGE_CACHE_ENABLED,
        "file_count": len(files),
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "max_size_mb": SD_IMAGE_CACHE_MAX_SIZE_MB,
        "cache_dir": str(_CACHE_DIR),
    }


def _maybe_evict() -> None:
    """Evict oldest files if total cache exceeds max size."""
    max_bytes = SD_IMAGE_CACHE_MAX_SIZE_MB * 1024 * 1024
    files = list(_CACHE_DIR.glob("*.b64"))
    total = sum(f.stat().st_size for f in files)

    if total <= max_bytes:
        return

    # Sort by access time (oldest first)
    files.sort(key=lambda f: f.stat().st_mtime)
    evicted = 0
    for f in files:
        if total <= max_bytes:
            break
        size = f.stat().st_size
        f.unlink()
        total -= size
        evicted += 1

    if evicted:
        logger.info("♻️ [Image Cache] Evicted %d files to stay under %dMB", evicted, SD_IMAGE_CACHE_MAX_SIZE_MB)
