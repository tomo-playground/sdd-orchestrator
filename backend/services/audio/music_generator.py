"""Stable Audio Open music generation service.

Mirrors the TTS model-loading pattern from scene_processing.py:
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

import soundfile as sf

from config import (
    SAO_CACHE_DIR,
    SAO_DEFAULT_DURATION,
    SAO_DEFAULT_STEPS,
    SAO_DEVICE,
    SAO_MAX_DURATION,
    SAO_MODEL_NAME,
    SAO_SAMPLE_RATE,
    logger,
)

# Global model cache (lazy-loaded on first use)
_sao_pipeline = None
_sao_lock = asyncio.Lock()
_inference_lock = threading.Lock()  # Protect concurrent inference


def _resolve_device() -> str:
    """Auto-detect the best available device."""
    if SAO_DEVICE != "auto":
        return SAO_DEVICE
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def _load_sao_pipeline():
    """Load the Stable Audio Open pipeline (blocking)."""
    import sys

    import torch
    from diffusers import DPMSolverMultistepScheduler, StableAudioPipeline

    # Model deserialization needs deeper recursion on some Python versions
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))

    device = _resolve_device()
    dtype = torch.float32 if device == "cpu" else torch.float16

    logger.info("[SAO] Loading model %s on %s (dtype=%s)...", SAO_MODEL_NAME, device, dtype)
    pipe = StableAudioPipeline.from_pretrained(SAO_MODEL_NAME, torch_dtype=dtype)
    # Replace default CosineDPMSolverMultistepScheduler (uses torchsde recursive
    # Brownian tree which hits Python recursion limit) with standard DPM solver.
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to(device)
    logger.info("[SAO] Model loaded successfully")
    return pipe


def get_sao_model_sync():
    """Synchronous getter for manual warmup."""
    global _sao_pipeline
    if _sao_pipeline is None:
        _sao_pipeline = _load_sao_pipeline()
    return _sao_pipeline


async def get_sao_model_async():
    """Async getter with lock — safe for concurrent requests."""
    global _sao_pipeline
    async with _sao_lock:
        if _sao_pipeline is not None:
            return _sao_pipeline
        loop = asyncio.get_event_loop()
        _sao_pipeline = await loop.run_in_executor(None, _load_sao_pipeline)
        return _sao_pipeline


def _music_cache_key(prompt: str, duration: float, seed: int, steps: int) -> str:
    """SHA256-based cache key for deterministic results."""
    raw = f"{prompt}|{duration}|{seed}|{steps}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_key: str) -> Path:
    return SAO_CACHE_DIR / f"{cache_key}.wav"


def generate_music(
    prompt: str,
    duration: float = SAO_DEFAULT_DURATION,
    seed: int = -1,
    num_inference_steps: int = SAO_DEFAULT_STEPS,
) -> tuple[bytes, int, int]:
    """Generate music from text prompt.

    Returns (wav_bytes, sample_rate, actual_seed).
    Uses file cache for deterministic seed results.
    """
    import torch

    duration = min(duration, SAO_MAX_DURATION)

    # Resolve seed
    if seed < 0:
        seed = int(torch.randint(0, 2**31, (1,)).item())

    # Check cache
    cache_key = _music_cache_key(prompt, duration, seed, num_inference_steps)
    cached = _cache_path(cache_key)
    if cached.exists():
        logger.info("[SAO] Cache hit: %s", cache_key)
        return cached.read_bytes(), SAO_SAMPLE_RATE, seed

    # Generate (thread-safe: one inference at a time)
    with _inference_lock:
        pipe = get_sao_model_sync()
        generator = torch.Generator(device=_resolve_device()).manual_seed(seed)

        logger.info(
            "[SAO] Generating: prompt=%r, duration=%.1fs, seed=%d, steps=%d",
            prompt[:60],
            duration,
            seed,
            num_inference_steps,
        )

        output = pipe(
            prompt=prompt,
            negative_prompt="low quality, noise, distortion",
            num_inference_steps=num_inference_steps,
            audio_end_in_s=duration,
            num_waveforms_per_prompt=1,
            generator=generator,
        )

    audio = output.audios[0].cpu().float().numpy().T  # (samples, channels)

    # Write to cache
    buf = io.BytesIO()
    sf.write(buf, audio, SAO_SAMPLE_RATE, format="WAV")
    wav_bytes = buf.getvalue()

    cached.write_bytes(wav_bytes)
    logger.info("[SAO] Generated and cached: %s (%d bytes)", cache_key, len(wav_bytes))

    return wav_bytes, SAO_SAMPLE_RATE, seed
