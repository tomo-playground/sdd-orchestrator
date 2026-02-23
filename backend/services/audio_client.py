"""HTTP client for Audio Server (TTS + MusicGen sidecar).

Pattern: SD WebUI client (services/generation.py) + Circuit Breaker (services/danbooru.py).
"""

from __future__ import annotations

import base64
import time

import httpx

from config import logger

# Circuit breaker state
_CIRCUIT_FAILURE_THRESHOLD = 3
_CIRCUIT_COOLDOWN_SEC = 60
_circuit_failures = 0
_circuit_open_until = 0.0


def _get_audio_server_config() -> tuple[str, float]:
    """Lazy import to avoid circular imports at module level."""
    from config import AUDIO_SERVER_URL, AUDIO_TIMEOUT_SECONDS

    return AUDIO_SERVER_URL, AUDIO_TIMEOUT_SECONDS


def _check_circuit() -> bool:
    """Return True if circuit is closed (requests allowed)."""
    global _circuit_failures, _circuit_open_until
    now = time.monotonic()
    if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD:
        if now < _circuit_open_until:
            return False
        logger.info("[AudioClient] Circuit breaker: retrying after cooldown")
        _circuit_failures = 0
    return True


def _record_success():
    global _circuit_failures
    _circuit_failures = 0


def _record_failure():
    global _circuit_failures, _circuit_open_until
    _circuit_failures += 1
    if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD:
        _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN_SEC
        logger.warning("[AudioClient] Circuit breaker OPEN (failures=%d)", _circuit_failures)


async def synthesize_tts(
    text: str,
    instruct: str = "",
    language: str = "korean",
    seed: int = -1,
    temperature: float = 0.7,
    top_p: float = 0.8,
    repetition_penalty: float = 1.0,
    max_new_tokens: int = 1024,
) -> tuple[bytes, int, float, bool]:
    """Call Audio Server /tts/synthesize.

    Returns (audio_bytes, sample_rate, duration, quality_passed).
    Raises httpx.HTTPStatusError or RuntimeError on failure.
    """
    if not _check_circuit():
        raise RuntimeError("Audio Server circuit breaker is open")

    url, timeout = _get_audio_server_config()

    payload = {
        "text": text,
        "instruct": instruct,
        "language": language,
        "seed": seed,
        "temperature": temperature,
        "top_p": top_p,
        "repetition_penalty": repetition_penalty,
        "max_new_tokens": max_new_tokens,
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
        _record_success()

        return (
            audio_bytes,
            data["sample_rate"],
            data["duration"],
            data["quality_passed"],
        )
    except Exception as e:
        _record_failure()
        logger.error("[AudioClient] TTS synthesis failed: %s", e)
        raise


async def generate_music(
    prompt: str,
    duration: float = 30.0,
    seed: int = -1,
) -> tuple[bytes, int, int]:
    """Call Audio Server /music/generate.

    Returns (wav_bytes, sample_rate, actual_seed).
    """
    if not _check_circuit():
        raise RuntimeError("Audio Server circuit breaker is open")

    url, timeout = _get_audio_server_config()

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
                timeout=timeout,
            )
            resp.raise_for_status()

        data = resp.json()
        wav_bytes = base64.b64decode(data["audio_base64"])
        _record_success()

        return wav_bytes, data["sample_rate"], data["actual_seed"]
    except Exception as e:
        _record_failure()
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
