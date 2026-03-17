"""Audio Server — TTS + SoVITS + MusicGen 통합 사이드카.

3엔진 통합: GPT-SoVITS(씬 TTS) + Qwen3-TTS(보이스 디자인) + MusicGen(BGM).
SoVITS는 Python 3.12 subprocess로 관리. Backend는 :8001만 호출.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from contextlib import asynccontextmanager

import soundfile as sf
from fastapi import FastAPI, HTTPException

from schemas import (  # noqa: F811
    HealthResponse,
    ModelStatus,
    MusicGenerateRequest,
    MusicGenerateResponse,
    SoVITSSynthesizeRequest,
    SoVITSSynthesizeResponse,
    TTSSynthesizeRequest,
    TTSSynthesizeResponse,
)
from services import music_engine, tts_engine
from services.tts_postprocess import trim_tts_audio, validate_tts_duration, validate_tts_quality

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("audio-server")


async def _idle_watchdog():
    """백그라운드 태스크: idle timeout 초과 시 TTS 모델 자동 언로드."""
    from config import MODEL_IDLE_TIMEOUT_SECONDS

    while True:
        await asyncio.sleep(60)  # 1분마다 체크
        if tts_engine.get_model() is None:
            continue
        idle = tts_engine.idle_seconds()
        if idle > MODEL_IDLE_TIMEOUT_SECONDS:
            logger.info(
                "[IdleWatchdog] TTS idle %.0fs > %ds, unloading...",
                idle,
                MODEL_IDLE_TIMEOUT_SECONDS,
            )
            await asyncio.to_thread(tts_engine.unload_model)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start audio server. Persistent mode preloads TTS at startup."""
    from config import MODEL_IDLE_TIMEOUT_SECONDS, SOVITS_ENABLED
    from services.sovits_process import sovits_manager

    persistent = MODEL_IDLE_TIMEOUT_SECONDS <= 0
    watchdog = None

    if persistent:
        logger.info("[Startup] Persistent mode — MusicGen preload, TTS on-demand (voice design only)")
        await asyncio.to_thread(music_engine.load_model)
        logger.info("[Startup] MusicGen loaded (CPU). TTS(Qwen3) loads on-demand for voice design.")
    else:
        logger.info("[Startup] On-demand mode — TTS loads on first request (idle=%ds)", MODEL_IDLE_TIMEOUT_SECONDS)
        watchdog = asyncio.create_task(_idle_watchdog())

    # GPT-SoVITS subprocess
    if SOVITS_ENABLED:
        started = await sovits_manager.start()
        if started:
            logger.info("[Startup] GPT-SoVITS ready (subprocess)")
        else:
            logger.warning("[Startup] GPT-SoVITS failed to start — SoVITS TTS unavailable")

    yield

    # Shutdown
    if SOVITS_ENABLED:
        await sovits_manager.stop()
    if watchdog:
        watchdog.cancel()
    logger.info("[Shutdown] Audio Server stopped")


app = FastAPI(title="Audio Server", lifespan=lifespan)


@app.post("/tts/synthesize", response_model=TTSSynthesizeResponse)
async def synthesize_tts(req: TTSSynthesizeRequest):
    """Generate TTS audio: synthesize -> post-process -> quality check -> WAV encode."""
    from config import TTS_CACHE_DIR

    # Resolve seed
    if req.seed < 0:
        import torch

        req.seed = int(torch.randint(0, 2**31, (1,)).item())

    # Korean text preprocessing (numbers → spoken Korean)
    synth_text = req.text
    if req.language.lower() in ("korean", "ko", "kr"):
        from services.text_preprocess import preprocess_korean

        synth_text = preprocess_korean(req.text)
        if synth_text != req.text:
            logger.info("[TTS] Preprocessed: %s → %s", req.text, synth_text)

    # Cache lookup — uses preprocessed text so cache key matches synthesis input
    cache_key = tts_engine.tts_cache_key(synth_text, req.instruct, req.seed, req.language)
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"
    if req.force and cache_path.exists():
        cache_path.unlink()
        logger.info("[TTS] force: cache deleted (%s)", cache_key)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        cached_bytes = cache_path.read_bytes()
        audio_b64 = base64.b64encode(cached_bytes).decode()
        # Read actual duration and sample rate from cached WAV
        info = sf.info(cache_path)
        return TTSSynthesizeResponse(
            audio_base64=audio_b64,
            sample_rate=info.samplerate,
            duration=round(info.duration, 2),
            quality_passed=True,
            cache_hit=True,
        )

    try:
        wavs, sr = await asyncio.to_thread(
            tts_engine.synthesize,
            text=synth_text,
            instruct=req.instruct,
            language=req.language,
            seed=req.seed,
            temperature=req.temperature,
            top_p=req.top_p,
            repetition_penalty=req.repetition_penalty,
            max_new_tokens=req.max_new_tokens,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"TTS model not ready: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}") from e

    # Post-process
    wav = trim_tts_audio(wavs[0], sr)
    duration = len(wav) / sr
    quality_passed = validate_tts_quality(wav, sr) and validate_tts_duration(wav, sr, 0.5)

    # Encode as WAV
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV")
    wav_bytes = buf.getvalue()

    # Store in cache
    cache_path.write_bytes(wav_bytes)

    audio_b64 = base64.b64encode(wav_bytes).decode()

    return TTSSynthesizeResponse(
        audio_base64=audio_b64,
        sample_rate=sr,
        duration=round(duration, 2),
        quality_passed=quality_passed,
        cache_hit=False,
    )


@app.post("/tts/sovits", response_model=SoVITSSynthesizeResponse)
async def synthesize_sovits(req: SoVITSSynthesizeRequest):
    """Proxy to GPT-SoVITS subprocess + post-processing."""
    from services.sovits_process import sovits_manager
    from services.tts_postprocess import trim_tts_audio, validate_tts_quality

    if not sovits_manager.is_running:
        raise HTTPException(status_code=503, detail="GPT-SoVITS is not running")

    try:
        raw_wav = await sovits_manager.synthesize(
            text=req.text,
            ref_audio_path=req.ref_audio_path,
            prompt_text=req.prompt_text,
            prompt_lang=req.prompt_lang,
            text_lang=req.text_lang,
            speed_factor=req.speed_factor,
            top_k=req.top_k,
            top_p=req.top_p,
            temperature=req.temperature,
            repetition_penalty=req.repetition_penalty,
            text_split_method=req.text_split_method,
            seed=req.seed,
            parallel_infer=req.parallel_infer,
            split_bucket=req.split_bucket,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    # Parse WAV → post-process (trim/decrackle/normalize) → quality check
    buf = io.BytesIO(raw_wav)
    audio_data, sr = sf.read(buf, dtype="float32")
    audio_data = trim_tts_audio(audio_data, sr, normalize=True)
    duration = len(audio_data) / sr
    quality_passed = validate_tts_quality(audio_data, sr)

    # Re-encode processed audio as WAV
    out_buf = io.BytesIO()
    sf.write(out_buf, audio_data, sr, format="WAV")
    audio_b64 = base64.b64encode(out_buf.getvalue()).decode()

    return SoVITSSynthesizeResponse(
        audio_base64=audio_b64,
        sample_rate=sr,
        duration=round(duration, 2),
        quality_passed=quality_passed,
    )


@app.post("/music/generate", response_model=MusicGenerateResponse)
async def generate_music(req: MusicGenerateRequest):
    """Generate music from text prompt."""
    try:
        wav_bytes, sample_rate, actual_seed, cache_hit = await asyncio.to_thread(
            music_engine.generate_music,
            prompt=req.prompt,
            duration=req.duration,
            seed=req.seed,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"MusicGen model not ready: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Music generation failed: {e}") from e

    audio_b64 = base64.b64encode(wav_bytes).decode()

    # Calculate actual duration from WAV bytes
    buf = io.BytesIO(wav_bytes)
    info = sf.info(buf)
    duration = info.duration

    return MusicGenerateResponse(
        audio_base64=audio_b64,
        sample_rate=sample_rate,
        actual_seed=actual_seed,
        duration=round(duration, 2),
        cache_hit=cache_hit,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Report model loading status (all 3 engines)."""
    from config import SOVITS_ENABLED
    from services.sovits_process import sovits_manager

    tts_model = tts_engine.get_model()
    music_model, _ = music_engine.get_model()

    models = [
        ModelStatus(
            name="gpt-sovits",
            loaded=sovits_manager.is_running if SOVITS_ENABLED else False,
            device="cuda",
        ),
        ModelStatus(
            name="qwen3-tts",
            loaded=tts_model is not None,
            device=tts_engine.get_device(),
        ),
        ModelStatus(
            name="musicgen-small",
            loaded=music_model is not None,
            device=music_engine.get_device(),
        ),
    ]

    return HealthResponse(status="ok", models=models)
