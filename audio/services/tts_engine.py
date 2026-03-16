"""Qwen3-TTS model loading and synthesis.

Manages global model instance with lazy loading.
"""

from __future__ import annotations

import hashlib
import logging

import torch
from qwen_tts import Qwen3TTSModel

from config import TTS_ATTN_IMPLEMENTATION, TTS_DEVICE, TTS_MODEL_NAME

logger = logging.getLogger("audio-server")

# Global model cache
_model: Qwen3TTSModel | None = None
_last_used: float = 0.0  # time.monotonic() of last synthesis


def _resolve_device() -> str:
    device = TTS_DEVICE
    if device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    return device


def _resolve_dtype(device: str) -> torch.dtype:
    """Select optimal dtype for the device.

    CUDA/CPU: float32 — Qwen3-TTS autoregressive generation requires
    full precision for stable output quality and consistent duration.
    MPS: bfloat16 — Apple Silicon requires bfloat16 for MPS compatibility.
    """
    if device == "mps":
        return torch.bfloat16
    return torch.float32


def load_model() -> Qwen3TTSModel:
    """Load the Qwen3-TTS model (blocking). Called at startup."""
    global _model
    if _model is not None:
        return _model

    device = _resolve_device()
    dtype = _resolve_dtype(device)
    logger.info("Loading Qwen3-TTS model (%s) on %s (dtype=%s)...", TTS_MODEL_NAME, device, dtype)

    model = Qwen3TTSModel.from_pretrained(
        TTS_MODEL_NAME,
        dtype=dtype,
        device_map=device,
        attn_implementation=TTS_ATTN_IMPLEMENTATION,
    )
    model.device = torch.device(device)

    _model = model
    logger.info("Qwen3-TTS model loaded successfully on %s", device)
    return _model


def get_model() -> Qwen3TTSModel | None:
    """Return the loaded model, or None if not yet loaded."""
    return _model


def get_device() -> str:
    """Return the resolved device string."""
    return _resolve_device()


def unload_model() -> bool:
    """GPU 메모리 해제를 위해 모델을 언로드한다. 언로드 성공 시 True."""
    global _model
    if _model is None:
        return False
    del _model
    _model = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    import gc

    gc.collect()
    logger.info("Qwen3-TTS model unloaded (GPU memory released)")
    return True


def touch() -> None:
    """마지막 사용 시각을 갱신한다."""
    global _last_used
    import time

    _last_used = time.monotonic()


def idle_seconds() -> float:
    """마지막 사용 이후 경과 시간(초)."""
    import time

    return time.monotonic() - _last_used if _last_used > 0 else 0.0


def synthesize(
    text: str,
    instruct: str,
    language: str,
    seed: int,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
    max_new_tokens: int,
) -> tuple[list, int]:
    """Run TTS synthesis. Returns (wavs, sample_rate).

    모델이 언로드 상태이면 자동 재로드.
    """
    model = get_model()
    if model is None:
        logger.info("TTS model not loaded, reloading on demand...")
        model = load_model()
    touch()

    torch.manual_seed(seed)
    wavs, sr = model.generate_voice_design(
        text=text,
        instruct=instruct,
        language=language,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        max_new_tokens=max_new_tokens,
    )
    return wavs, sr


def tts_cache_key(text: str, instruct: str, seed: int, language: str) -> str:
    """SHA256-based cache key for TTS results."""
    raw = f"{text}|{instruct}|{seed}|{language}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
