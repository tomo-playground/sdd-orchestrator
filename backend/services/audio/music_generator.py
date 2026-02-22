"""MusicGen Small music generation service.

Uses facebook/musicgen-small (300M) via HuggingFace transformers.
- Global model + asyncio.Lock for thread safety
- Lazy loading (first use) instead of startup preload
- SHA256 cache keying for deterministic results
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import threading
from pathlib import Path

import scipy.io.wavfile

from config import (
    MUSICGEN_CACHE_DIR,
    MUSICGEN_DEFAULT_DURATION,
    MUSICGEN_DEVICE,
    MUSICGEN_MAX_DURATION,
    MUSICGEN_MODEL_NAME,
    MUSICGEN_SAMPLE_RATE,
    MUSICGEN_TOKENS_PER_SECOND,
    logger,
)

# Global model cache (lazy-loaded on first use)
_musicgen_model = None
_musicgen_processor = None
_musicgen_lock = asyncio.Lock()
_inference_lock = threading.Lock()  # Protect concurrent inference


def _resolve_device() -> str:
    """Auto-detect the best available device."""
    if MUSICGEN_DEVICE != "auto":
        return MUSICGEN_DEVICE
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def _load_musicgen():
    """Load the MusicGen model and processor (blocking)."""
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    device = _resolve_device()
    logger.info("[MusicGen] Loading model %s on %s...", MUSICGEN_MODEL_NAME, device)

    processor = AutoProcessor.from_pretrained(MUSICGEN_MODEL_NAME)
    model = MusicgenForConditionalGeneration.from_pretrained(MUSICGEN_MODEL_NAME)
    model = model.to(device)

    logger.info("[MusicGen] Model loaded successfully")
    return model, processor


def get_musicgen_model_sync():
    """Synchronous getter for manual warmup."""
    global _musicgen_model, _musicgen_processor
    if _musicgen_model is None:
        _musicgen_model, _musicgen_processor = _load_musicgen()
    return _musicgen_model, _musicgen_processor


async def get_musicgen_model_async():
    """Async getter with lock - safe for concurrent requests."""
    global _musicgen_model, _musicgen_processor
    async with _musicgen_lock:
        if _musicgen_model is not None:
            return _musicgen_model, _musicgen_processor
        _musicgen_model, _musicgen_processor = await asyncio.to_thread(_load_musicgen)
        return _musicgen_model, _musicgen_processor


def _music_cache_key(prompt: str, duration: float, seed: int) -> str:
    """SHA256-based cache key for deterministic results."""
    raw = f"{prompt}|{duration}|{seed}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_key: str) -> Path:
    return MUSICGEN_CACHE_DIR / f"{cache_key}.wav"


def generate_music(
    prompt: str,
    duration: float = MUSICGEN_DEFAULT_DURATION,
    seed: int = -1,
) -> tuple[bytes, int, int]:
    """Generate music from text prompt.

    Returns (wav_bytes, sample_rate, actual_seed).
    Uses file cache for deterministic seed results.
    """
    import torch

    duration = min(duration, MUSICGEN_MAX_DURATION)

    # Resolve seed
    if seed < 0:
        seed = int(torch.randint(0, 2**31, (1,)).item())

    # Check cache
    cache_key = _music_cache_key(prompt, duration, seed)
    cached = _cache_path(cache_key)
    if cached.exists():
        logger.info("[MusicGen] Cache hit: %s", cache_key)
        return cached.read_bytes(), MUSICGEN_SAMPLE_RATE, seed

    # Generate (thread-safe: one inference at a time)
    with _inference_lock:
        model, processor = get_musicgen_model_sync()
        device = _resolve_device()

        # Calculate max_new_tokens from duration
        max_new_tokens = int(duration * MUSICGEN_TOKENS_PER_SECOND)

        logger.info(
            "[MusicGen] Generating: prompt=%r, duration=%.1fs, seed=%d, tokens=%d",
            prompt[:60],
            duration,
            seed,
            max_new_tokens,
        )

        inputs = processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        ).to(device)

        torch.manual_seed(seed)
        audio_values = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
        )

    # audio_values shape: (batch, 1, samples) -> squeeze to (samples,)
    audio = audio_values[0, 0].cpu().float().numpy()

    # Write to cache as WAV
    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, MUSICGEN_SAMPLE_RATE, audio)
    wav_bytes = buf.getvalue()

    cached.write_bytes(wav_bytes)
    logger.info("[MusicGen] Generated and cached: %s (%d bytes)", cache_key, len(wav_bytes))

    return wav_bytes, MUSICGEN_SAMPLE_RATE, seed
