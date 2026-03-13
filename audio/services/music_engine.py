"""MusicGen music generation service.

Uses facebook/musicgen-medium (1.5B) via HuggingFace transformers.
On-demand GPU loading: load model → generate → unload to free VRAM.
"""

from __future__ import annotations

import hashlib
import io
import logging
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
)

logger = logging.getLogger("audio-server")

_inference_lock = threading.Lock()


def _resolve_device() -> str:
    if MUSICGEN_DEVICE != "auto":
        return MUSICGEN_DEVICE
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def _load_model_to_device():
    """Load model and processor onto the resolved device. Returns (model, processor, device)."""
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    device = _resolve_device()
    logger.info("[MusicGen] Loading model %s on %s...", MUSICGEN_MODEL_NAME, device)

    processor = AutoProcessor.from_pretrained(MUSICGEN_MODEL_NAME)
    model = MusicgenForConditionalGeneration.from_pretrained(MUSICGEN_MODEL_NAME)
    model = model.to(device)

    logger.info("[MusicGen] Model loaded successfully")
    return model, processor, device


def _unload_model(model, processor):
    """Delete model/processor and free GPU memory."""
    import gc

    del model
    del processor
    gc.collect()

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("[MusicGen] GPU memory released")
    except Exception:
        pass


def load_model():
    """No-op for backward compatibility. Model is now loaded on-demand."""
    logger.info("[MusicGen] On-demand mode: model will be loaded per request")
    return None, None


def get_model():
    """Return (None, None). Model is no longer cached globally."""
    return None, None


def get_device() -> str:
    return _resolve_device()


def music_cache_key(prompt: str, duration: float, seed: int) -> str:
    """SHA256-based cache key."""
    raw = f"{prompt}|{duration}|{seed}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_key: str) -> Path:
    return MUSICGEN_CACHE_DIR / f"{cache_key}.wav"


def generate_music(
    prompt: str,
    duration: float = MUSICGEN_DEFAULT_DURATION,
    seed: int = -1,
) -> tuple[bytes, int, int, bool]:
    """Generate music from text prompt.

    Loads model on-demand and unloads after generation to free VRAM.
    Returns (wav_bytes, sample_rate, actual_seed, cache_hit).
    """
    import torch

    duration = min(duration, MUSICGEN_MAX_DURATION)

    if seed < 0:
        seed = int(torch.randint(0, 2**31, (1,)).item())

    cache_key = music_cache_key(prompt, duration, seed)
    cached = _cache_path(cache_key)
    if cached.exists():
        logger.info("[MusicGen] Cache hit: %s", cache_key)
        return cached.read_bytes(), MUSICGEN_SAMPLE_RATE, seed, True

    with _inference_lock:
        model, processor, device = _load_model_to_device()
        try:
            max_new_tokens = int(duration * MUSICGEN_TOKENS_PER_SECOND)

            logger.info(
                "[MusicGen] Generating: prompt=%r, duration=%.1fs, seed=%d, tokens=%d",
                prompt[:60],
                duration,
                seed,
                max_new_tokens,
            )

            inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
            torch.manual_seed(seed)
            audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True)
        finally:
            _unload_model(model, processor)

    audio = audio_values[0, 0].cpu().float().numpy()

    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, MUSICGEN_SAMPLE_RATE, audio)
    wav_bytes = buf.getvalue()

    cached.write_bytes(wav_bytes)
    logger.info("[MusicGen] Generated and cached: %s (%d bytes)", cache_key, len(wav_bytes))

    return wav_bytes, MUSICGEN_SAMPLE_RATE, seed, False
