"""Audio Server — TTS + MusicGen sidecar service.

Runs as an independent FastAPI app, serving TTS synthesis and music generation
over HTTP. Backend communicates via audio_client.py.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from contextlib import asynccontextmanager

import soundfile as sf
from fastapi import FastAPI, HTTPException

from schemas import (
    HealthResponse,
    ModelStatus,
    MusicGenerateRequest,
    MusicGenerateResponse,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models on startup."""
    logger.info("[Startup] Loading TTS model...")
    await asyncio.to_thread(tts_engine.load_model)
    logger.info("[Startup] Loading MusicGen model...")
    await asyncio.to_thread(music_engine.load_model)
    logger.info("[Startup] All models loaded")
    yield
    logger.info("[Shutdown] Audio Server stopped")


app = FastAPI(title="Audio Server", lifespan=lifespan)


@app.post("/tts/synthesize", response_model=TTSSynthesizeResponse)
async def synthesize_tts(req: TTSSynthesizeRequest):
    """Generate TTS audio: synthesize -> post-process -> quality check -> MP3 encode."""
    from config import TTS_CACHE_DIR

    # Cache lookup
    cache_key = tts_engine.tts_cache_key(req.text, req.instruct, req.seed, req.language)
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"
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

    # Resolve seed
    if req.seed < 0:
        import torch

        req.seed = int(torch.randint(0, 2**31, (1,)).item())

    try:
        wavs, sr = await asyncio.to_thread(
            tts_engine.synthesize,
            text=req.text,
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


@app.post("/music/generate", response_model=MusicGenerateResponse)
async def generate_music(req: MusicGenerateRequest):
    """Generate music from text prompt."""
    try:
        wav_bytes, sample_rate, actual_seed = await asyncio.to_thread(
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
    import scipy.io.wavfile

    buf = io.BytesIO(wav_bytes)
    sr, data = scipy.io.wavfile.read(buf)
    duration = len(data) / sr

    # Check if this was a cache hit (by checking if cache file existed before)
    cache_key = music_engine.music_cache_key(req.prompt, req.duration, actual_seed)
    cache_hit = (music_engine._cache_path(cache_key)).exists()

    return MusicGenerateResponse(
        audio_base64=audio_b64,
        sample_rate=sample_rate,
        actual_seed=actual_seed,
        duration=round(duration, 2),
        cache_hit=cache_hit,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Report model loading status."""
    tts_model = tts_engine.get_model()
    music_model, _ = music_engine.get_model()

    models = [
        ModelStatus(
            name="qwen3-tts",
            loaded=tts_model is not None,
            device=tts_engine.get_device() if tts_model else "none",
        ),
        ModelStatus(
            name="musicgen-small",
            loaded=music_model is not None,
            device=music_engine.get_device() if music_model else "none",
        ),
    ]

    all_loaded = all(m.loaded for m in models)
    status = "ok" if all_loaded else "loading"

    return HealthResponse(status=status, models=models)
