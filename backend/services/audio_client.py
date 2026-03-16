"""HTTP client for Audio Server (TTS + MusicGen sidecar).

Pattern: SD WebUI client (services/generation.py) + Circuit Breaker (services/danbooru.py).
"""

from __future__ import annotations

import base64
import time

import httpx

from config import TTS_NATURALNESS_SUFFIX, logger

# Circuit breaker state — per-task isolation so concurrent video builds
# don't interfere with each other's breaker state.
_CIRCUIT_SCENE_FAILURE_THRESHOLD = 3
_CIRCUIT_COOLDOWN_SEC = 60
_circuit_state: dict[str, dict] = {}  # task_id -> {"failures": int, "open_until": float}


def _get_audio_server_config() -> tuple[str, float]:
    """Lazy import to avoid circular imports at module level."""
    from config import AUDIO_SERVER_URL, AUDIO_TIMEOUT_SECONDS

    return AUDIO_SERVER_URL, AUDIO_TIMEOUT_SECONDS


def _get_state(task_id: str) -> dict:
    """Get or create circuit breaker state for a task."""
    if task_id not in _circuit_state:
        _circuit_state[task_id] = {"failures": 0, "open_until": 0.0}
    return _circuit_state[task_id]


def _check_circuit(task_id: str = "default") -> bool:
    """Return True if circuit is closed (requests allowed)."""
    state = _get_state(task_id)
    now = time.monotonic()
    if state["failures"] >= _CIRCUIT_SCENE_FAILURE_THRESHOLD:
        if now < state["open_until"]:
            return False
        logger.info("[AudioClient] Circuit breaker (%s): retrying after cooldown", task_id)
        state["failures"] = 0
    return True


def record_scene_success(task_id: str = "default") -> None:
    """Call after a scene's TTS/music generation succeeds (possibly after retries)."""
    state = _get_state(task_id)
    state["failures"] = 0


def record_scene_failure(task_id: str = "default") -> None:
    """Call after a scene exhausts all retries with no usable audio."""
    state = _get_state(task_id)
    state["failures"] += 1
    if state["failures"] >= _CIRCUIT_SCENE_FAILURE_THRESHOLD:
        state["open_until"] = time.monotonic() + _CIRCUIT_COOLDOWN_SEC
        logger.warning(
            "[AudioClient] Circuit breaker OPEN (%s: %d consecutive scenes failed)",
            task_id,
            state["failures"],
        )


async def synthesize_tts(
    text: str,
    instruct: str = "",
    language: str = "korean",
    seed: int = -1,
    temperature: float = 0.7,
    top_p: float = 0.8,
    repetition_penalty: float = 1.0,
    max_new_tokens: int = 1024,
    task_id: str = "default",
    force: bool = False,
) -> tuple[bytes, int, float, bool]:
    """Call Audio Server /tts/synthesize.

    Returns (audio_bytes, sample_rate, duration, quality_passed).
    Raises httpx.HTTPStatusError or RuntimeError on failure.
    """
    if not _check_circuit(task_id):
        raise RuntimeError("Audio Server circuit breaker is open")

    url, timeout = _get_audio_server_config()

    # Append naturalness suffix to reduce robotic/AI-sounding output
    if TTS_NATURALNESS_SUFFIX:
        instruct = f"{instruct}, {TTS_NATURALNESS_SUFFIX}" if instruct else TTS_NATURALNESS_SUFFIX

    payload = {
        "text": text,
        "instruct": instruct,
        "language": language,
        "seed": seed,
        "temperature": temperature,
        "top_p": top_p,
        "repetition_penalty": repetition_penalty,
        "max_new_tokens": max_new_tokens,
        "force": force,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{url}/tts/synthesize",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()

        data = resp.json()
        audio_bytes = base64.b64decode(data["audio_base64"])

        return (
            audio_bytes,
            data["sample_rate"],
            data["duration"],
            data["quality_passed"],
        )
    except Exception as e:
        logger.error("[AudioClient] TTS synthesis failed: %s", e)
        raise


async def generate_music(
    prompt: str,
    duration: float = 30.0,
    seed: int = -1,
    task_id: str = "default",
) -> tuple[bytes, int, int]:
    """Call Audio Server /music/generate.

    Returns (wav_bytes, sample_rate, actual_seed).
    """
    if not _check_circuit(task_id):
        raise RuntimeError("Audio Server circuit breaker is open")

    from config import MUSIC_TIMEOUT_SECONDS

    url, _ = _get_audio_server_config()

    payload = {
        "prompt": prompt,
        "duration": duration,
        "seed": seed,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{url}/music/generate",
                json=payload,
                timeout=MUSIC_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()

        data = resp.json()
        wav_bytes = base64.b64decode(data["audio_base64"])

        return wav_bytes, data["sample_rate"], data["actual_seed"]
    except Exception as e:
        logger.error("[AudioClient] Music generation failed: %s", e)
        raise


async def check_health() -> dict:
    """Call Audio Server /health. Returns parsed JSON response."""
    url, _ = _get_audio_server_config()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/health", timeout=5.0)
            resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("[AudioClient] Health check failed: %s", e)
        return {"status": "error", "models": []}
