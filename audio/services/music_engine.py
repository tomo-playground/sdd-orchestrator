"""MusicGen Small music generation service.

Uses facebook/musicgen-small (300M) via HuggingFace transformers.
Global model + threading lock for inference safety.
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

# Global model cache (lazy-loaded on first use)
_musicgen_model = None
_musicgen_processor = None
_inference_lock = threading.Lock()


def _resolve_device() -> str:
    if MUSICGEN_DEVICE != "auto":
        return MUSICGEN_DEVICE
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def load_model():
    """Load the MusicGen model and processor (blocking). Called at startup."""
    global _musicgen_model, _musicgen_processor
    if _musicgen_model is not None:
        return _musicgen_model, _musicgen_processor

    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    device = _resolve_device()
    logger.info("[MusicGen] Loading model %s on %s...", MUSICGEN_MODEL_NAME, device)

    processor = AutoProcessor.from_pretrained(MUSICGEN_MODEL_NAME)
    model = MusicgenForConditionalGeneration.from_pretrained(MUSICGEN_MODEL_NAME)
    model = model.to(device)

    _musicgen_model = model
    _musicgen_processor = processor
    logger.info("[MusicGen] Model loaded successfully")
    return _musicgen_model, _musicgen_processor


def get_model():
    """Return (model, processor) tuple or (None, None) if not loaded."""
    return _musicgen_model, _musicgen_processor


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
) -> tuple[bytes, int, int]:
    """Generate music from text prompt.

    Returns (wav_bytes, sample_rate, actual_seed).
    """
    import torch

    duration = min(duration, MUSICGEN_MAX_DURATION)

    if seed < 0:
        seed = int(torch.randint(0, 2**31, (1,)).item())

    cache_key = music_cache_key(prompt, duration, seed)
    cached = _cache_path(cache_key)
    if cached.exists():
        logger.info("[MusicGen] Cache hit: %s", cache_key)
        return cached.read_bytes(), MUSICGEN_SAMPLE_RATE, seed

    with _inference_lock:
        model, processor = _musicgen_model, _musicgen_processor
        if model is None or processor is None:
            raise RuntimeError("MusicGen model not loaded")

        device = _resolve_device()
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

    audio = audio_values[0, 0].cpu().float().numpy()

    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, MUSICGEN_SAMPLE_RATE, audio)
    wav_bytes = buf.getvalue()

    cached.write_bytes(wav_bytes)
    logger.info("[MusicGen] Generated and cached: %s (%d bytes)", cache_key, len(wav_bytes))

    return wav_bytes, MUSICGEN_SAMPLE_RATE, seed
