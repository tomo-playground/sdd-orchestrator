"""Audio Server configuration — TTS and MusicGen constants.

All values sourced from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
import pathlib

# --- TTS Configuration ---
TTS_MODEL_NAME = os.getenv("TTS_MODEL_NAME", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
TTS_DEVICE = os.getenv("TTS_DEVICE", "auto")  # "auto" | "mps" | "cpu"
TTS_ATTN_IMPLEMENTATION = os.getenv("TTS_ATTN_IMPLEMENTATION", "sdpa")

# Generation parameters
TTS_TEMPERATURE = float(os.getenv("TTS_TEMPERATURE", "0.7"))
TTS_TOP_P = float(os.getenv("TTS_TOP_P", "0.8"))
TTS_REPETITION_PENALTY = float(os.getenv("TTS_REPETITION_PENALTY", "1.05"))
TTS_MAX_NEW_TOKENS = int(os.getenv("TTS_MAX_NEW_TOKENS", "1024"))
TTS_DEFAULT_LANGUAGE = os.getenv("TTS_DEFAULT_LANGUAGE", "korean")

# Post-processing
TTS_AUDIO_TRIM_TOP_DB = int(os.getenv("TTS_AUDIO_TRIM_TOP_DB", "60"))
TTS_AUDIO_FADE_MS = int(os.getenv("TTS_AUDIO_FADE_MS", "15"))
TTS_SILENCE_MAX_MS = int(os.getenv("TTS_SILENCE_MAX_MS", "800"))

# --- MusicGen Configuration ---
MUSICGEN_MODEL_NAME = os.getenv("MUSICGEN_MODEL_NAME", "facebook/musicgen-small")
MUSICGEN_DEVICE = os.getenv("MUSICGEN_DEVICE", "auto")
MUSICGEN_DEFAULT_DURATION = float(os.getenv("MUSICGEN_DEFAULT_DURATION", "30.0"))
MUSICGEN_MAX_DURATION = float(os.getenv("MUSICGEN_MAX_DURATION", "60.0"))
MUSICGEN_SAMPLE_RATE = int(os.getenv("MUSICGEN_SAMPLE_RATE", "32000"))
MUSICGEN_TOKENS_PER_SECOND = 50  # EnCodec: 50 auto-regressive steps per second

# --- GPT-SoVITS Subprocess ---
SOVITS_ENABLED = os.getenv("SOVITS_ENABLED", "true").lower() == "true"
SOVITS_DIR = os.getenv("SOVITS_DIR", str(pathlib.Path.home() / "Workspace" / "GPT-SoVITS"))
SOVITS_VENV = os.getenv("SOVITS_VENV", "")  # 비어있으면 SOVITS_DIR/.venv
SOVITS_PORT = int(os.getenv("SOVITS_PORT", "9880"))
SOVITS_CONFIG = os.getenv("SOVITS_CONFIG", "GPT_SoVITS/configs/tts_infer.yaml")
SOVITS_STARTUP_TIMEOUT = int(os.getenv("SOVITS_STARTUP_TIMEOUT", "120"))
CUDA_HOME = os.getenv("CUDA_HOME", "/usr/local/cuda-12.8")

# --- Idle Auto-Unload ---
# 0 = persistent mode (시작 시 로드, 언로드 안 함)
# >0 = on-demand mode (N초간 요청 없으면 자동 언로드)
MODEL_IDLE_TIMEOUT_SECONDS = int(os.getenv("MODEL_IDLE_TIMEOUT_SECONDS", "0"))  # 기본: 상주

# --- Cache ---
_default_cache = "/app/cache" if pathlib.Path("/app").exists() else str(pathlib.Path.home() / ".cache" / "audio-server")
CACHE_DIR = pathlib.Path(os.getenv("CACHE_DIR", _default_cache))
TTS_CACHE_DIR = CACHE_DIR / "tts"
MUSICGEN_CACHE_DIR = CACHE_DIR / "music"

for _d in (CACHE_DIR, TTS_CACHE_DIR, MUSICGEN_CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
