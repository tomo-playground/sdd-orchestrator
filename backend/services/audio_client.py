"""HTTP client for Audio Server (TTS + MusicGen sidecar).

Pattern: SD WebUI client (services/generation.py) + Circuit Breaker (services/danbooru.py).
"""

from __future__ import annotations

import asyncio
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


async def _ensure_server_reachable() -> None:
    """오디오 서버 연결 가능 여부만 확인한다. 모델은 on-demand 로드."""
    health = await check_health()
    if health.get("status") == "error":
        raise RuntimeError("오디오 서버에 연결할 수 없습니다. 'run_audio.sh start'로 서버를 시작해주세요.")


def _extract_server_error(resp: httpx.Response) -> str:
    """오디오 서버 HTTP 에러 응답에서 detail 메시지를 추출한다."""
    try:
        data = resp.json()
        if isinstance(data, dict) and "detail" in data:
            return str(data["detail"])
    except Exception:
        pass
    return f"HTTP {resp.status_code}"


def _normalize_korean_text(text: str) -> str:
    """한국어 텍스트 정규화 — 숫자/영어/특수문자를 SoVITS G2P가 처리 가능한 형태로 변환."""
    import re  # noqa: PLC0415

    # 숫자+단위 변환 (기본적인 케이스만)
    text = re.sub(r"(\d+)%", r"\1퍼센트", text)
    text = re.sub(r"(\d+)원", lambda m: _num_to_korean(int(m.group(1))) + "원", text)
    text = re.sub(r"(\d+)개", lambda m: _num_to_korean(int(m.group(1))) + "개", text)
    text = re.sub(r"(\d+)명", lambda m: _num_to_korean(int(m.group(1))) + "명", text)
    # 남은 순수 숫자
    text = re.sub(r"\b(\d+)\b", lambda m: _num_to_korean(int(m.group(1))), text)
    # 특수문자 정리
    text = text.replace("...", "…").replace("~", "")
    return text


def _num_to_korean(n: int) -> str:
    """정수를 한국어 읽기로 변환 (간단 버전)."""
    if n == 0:
        return "영"
    units = ["", "만", "억"]
    parts = []
    for u in units:
        if n == 0:
            break
        chunk = n % 10000
        if chunk > 0:
            parts.append(f"{chunk}{u}")
        n //= 10000
    return "".join(reversed(parts))


async def _synthesize_sovits(
    text: str,
    ref_audio_path: str,
    ref_text: str = "",
    task_id: str = "default",
) -> tuple[bytes, int, float, bool]:
    """Call GPT-SoVITS /tts endpoint. Returns (wav_bytes, sample_rate, duration, quality_passed)."""
    from config import SOVITS_SERVER_URL  # noqa: PLC0415

    text = _normalize_korean_text(text)

    payload = {
        "text": text,
        "text_lang": "ko",
        "ref_audio_path": ref_audio_path,
        "prompt_text": ref_text,
        "prompt_lang": "ko",
        "speed_factor": 1.0,
        "media_type": "wav",
        "streaming_mode": False,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SOVITS_SERVER_URL}/tts",
            json=payload,
            timeout=180,
        )
        if not resp.is_success:
            detail = _extract_server_error(resp)
            raise RuntimeError(f"SoVITS 합성 실패: {detail}")

    # SoVITS returns raw WAV bytes
    import io  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415
    import soundfile as sf  # noqa: PLC0415

    audio_data, sr = sf.read(io.BytesIO(resp.content))
    duration = len(audio_data) / sr
    # Quality check: not silent
    rms = float(np.sqrt(np.mean(audio_data**2)))
    quality_passed = rms > 0.001

    logger.info("[SoVITS] Generated: %.1fs, sr=%d, quality=%s", duration, sr, quality_passed)
    return resp.content, sr, duration, quality_passed


async def _synthesize_qwen3(
    text: str,
    instruct: str = "",
    language: str = "korean",
    seed: int = -1,
    temperature: float = 0.7,
    top_p: float = 0.8,
    repetition_penalty: float = 1.0,
    max_new_tokens: int = 1024,
    force: bool = False,
) -> tuple[bytes, int, float, bool]:
    """Call Qwen3-TTS Audio Server /tts/synthesize (legacy fallback)."""
    url, timeout = _get_audio_server_config()

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

    async with httpx.AsyncClient() as client:
        resp = None
        for _retry in range(3):
            resp = await client.post(f"{url}/tts/synthesize", json=payload, timeout=timeout)
            if resp.status_code != 503 or _retry >= 2:
                break
            logger.info("[AudioClient] TTS 503 (model loading), waiting 15s... (%d/2)", _retry + 1)
            await asyncio.sleep(15)
        if not resp.is_success:
            detail = _extract_server_error(resp)
            raise RuntimeError(f"Qwen3 TTS 합성 실패: {detail}")

    data = resp.json()
    audio_bytes = base64.b64decode(data["audio_base64"])
    return audio_bytes, data["sample_rate"], data["duration"], data["quality_passed"]


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
    ref_audio_path: str | None = None,
    ref_text: str = "",
) -> tuple[bytes, int, float, bool]:
    """TTS synthesis with SoVITS → Qwen3 fallback chain.

    If ref_audio_path is provided, uses GPT-SoVITS for consistent voice cloning.
    Falls back to Qwen3-TTS on SoVITS failure.
    Returns (audio_bytes, sample_rate, duration, quality_passed).
    """
    if not _check_circuit(task_id):
        raise RuntimeError("Audio Server circuit breaker is open")

    # SoVITS path: reference audio available
    if ref_audio_path:
        try:
            result = await _synthesize_sovits(text, ref_audio_path, ref_text, task_id)
            logger.info("[TTS] SoVITS success: '%s...'", text[:30])
            return result
        except Exception as e:
            logger.warning("[TTS] SoVITS failed, falling back to Qwen3: %s", e)

    # Qwen3 fallback (or primary if no ref_audio)
    try:
        await _ensure_server_reachable()
        result = await _synthesize_qwen3(
            text, instruct, language, seed, temperature, top_p, repetition_penalty, max_new_tokens, force,
        )
        logger.info("[TTS] Qwen3 success: '%s...'", text[:30])
        return result
    except Exception as e:
        logger.error("[AudioClient] TTS synthesis failed (all engines): %s", e)
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

    await _ensure_server_reachable()

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
            if not resp.is_success:
                detail = _extract_server_error(resp)
                raise RuntimeError(f"BGM 생성 실패: {detail}")

        data = resp.json()
        wav_bytes = base64.b64decode(data["audio_base64"])

        return wav_bytes, data["sample_rate"], data["actual_seed"]
    except RuntimeError:
        raise
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
