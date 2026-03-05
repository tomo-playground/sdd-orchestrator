"""TTS preview: single scene + batch generation.

Reuses render-pipeline TTS helpers and cache keys.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from dataclasses import dataclass

from sqlalchemy.orm import Session

from config import (
    TTS_CACHE_DIR,
    TTS_DEFAULT_SEED,
    TTS_MAX_NEW_TOKENS_BASE,
    TTS_MAX_NEW_TOKENS_CAP,
    TTS_MAX_NEW_TOKENS_PER_CHAR,
    TTS_PREVIEW_BATCH_CONCURRENCY,
    TTS_REPETITION_PENALTY,
    TTS_TEMPERATURE,
    TTS_TOP_P,
    logger,
)
from schemas import (
    BatchTTSPreviewItem,
    BatchTTSPreviewRequest,
    BatchTTSPreviewResponse,
    SceneTTSPreviewRequest,
    SceneTTSPreviewResponse,
)
from services.asset_service import AssetService
from services.storage import get_storage

_TTS_BATCH_SEMAPHORE = asyncio.Semaphore(TTS_PREVIEW_BATCH_CONCURRENCY)


@dataclass
class _TtsGenResult:
    """Internal result of TTS generation (no DB write)."""

    audio_bytes: bytes
    duration: float
    cache_key: str
    cached: bool
    voice_seed: int


async def _generate_scene_tts(req: SceneTTSPreviewRequest) -> _TtsGenResult:
    """Generate TTS audio without any DB writes (pure I/O + cache)."""
    from services.audio_client import synthesize_tts
    from services.video.tts_helpers import (
        get_preset_voice_info,
        get_speaker_voice_preset,
        translate_voice_prompt,
        tts_cache_key,
    )
    from services.video.utils import clean_script_for_tts, has_speakable_content

    script = req.script.strip()
    if not script or not has_speakable_content(script):
        raise ValueError("스크립트에 TTS로 변환할 내용이 없습니다.")

    cleaned = clean_script_for_tts(script)

    # Resolve voice preset
    voice_preset_id = req.voice_preset_id
    if not voice_preset_id and req.storyboard_id:
        voice_preset_id = get_speaker_voice_preset(req.storyboard_id, req.speaker)

    # Resolve voice design + seed
    voice_design = req.voice_design_prompt
    voice_seed: int | None = None

    if voice_preset_id:
        preset_prompt, preset_seed = get_preset_voice_info(voice_preset_id)
        if not voice_design and preset_prompt:
            voice_design = preset_prompt
        if preset_seed is not None:
            voice_seed = preset_seed

    # Apply scene emotion
    if req.scene_emotion and req.scene_emotion.strip():
        voice_design = f"{voice_design}, {req.scene_emotion}" if voice_design else req.scene_emotion

    if voice_design:
        voice_design = translate_voice_prompt(voice_design)

    if voice_seed is None:
        voice_seed = TTS_DEFAULT_SEED

    # Build cache key (identical to render pipeline)
    cache_key = tts_cache_key(cleaned, voice_preset_id, voice_design, req.language)
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"

    # Force regenerate: delete existing cache
    if req.force_regenerate and cache_path.exists():
        cache_path.unlink()
        logger.info("[Preview] TTS cache deleted (force): %s", cache_key)

    # Check cache
    if cache_path.exists():
        audio_bytes = cache_path.read_bytes()
        duration = _wav_duration(audio_bytes)
        logger.info("[Preview] TTS cache hit: %s (%.1fs)", cache_key, duration)
        return _TtsGenResult(audio_bytes, duration, cache_key, cached=True, voice_seed=voice_seed)

    # Generate TTS
    max_tokens = min(
        TTS_MAX_NEW_TOKENS_BASE + len(cleaned) * TTS_MAX_NEW_TOKENS_PER_CHAR,
        TTS_MAX_NEW_TOKENS_CAP,
    )

    audio_bytes, _sr, duration, _quality = await synthesize_tts(
        text=cleaned,
        instruct=voice_design or "",
        language=req.language,
        seed=voice_seed,
        temperature=TTS_TEMPERATURE,
        top_p=TTS_TOP_P,
        repetition_penalty=TTS_REPETITION_PENALTY,
        max_new_tokens=max_tokens,
    )

    # Save to TTS cache (same location as render pipeline)
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio_bytes)
    logger.info("[Preview] TTS generated + cached: %s (%.1fs)", cache_key, duration)

    return _TtsGenResult(audio_bytes, duration, cache_key, cached=False, voice_seed=voice_seed)


def _save_audio_asset(db: Session, audio_bytes: bytes, cache_key: str):
    """Save audio bytes to storage and register as temp asset."""
    digest = hashlib.sha256(audio_bytes).hexdigest()[:16]
    file_name = f"tts_preview_{digest}.wav"
    storage_key = f"previews/tts/{file_name}"

    storage = get_storage()
    storage.save(storage_key, audio_bytes, content_type="audio/wav")

    asset_svc = AssetService(db)
    return asset_svc.register_asset(
        file_name=file_name,
        file_type="audio",
        storage_key=storage_key,
        owner_type="tts_preview",
        is_temp=True,
        file_size=len(audio_bytes),
        mime_type="audio/wav",
        checksum=AssetService.compute_checksum(audio_bytes),
    )


def _wav_duration(wav_bytes: bytes) -> float:
    """Calculate duration of WAV audio from bytes."""
    import wave

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate if rate > 0 else 0.0


# ── Public API ──────────────────────────────────────────


async def preview_scene_tts(
    req: SceneTTSPreviewRequest,
    db: Session,
) -> SceneTTSPreviewResponse:
    """Generate TTS preview for a single scene. Cache-compatible with render pipeline."""
    gen = await _generate_scene_tts(req)
    asset = _save_audio_asset(db, gen.audio_bytes, gen.cache_key)

    return SceneTTSPreviewResponse(
        audio_url=asset.url,
        duration=gen.duration,
        cache_key=gen.cache_key,
        cached=gen.cached,
        voice_seed=gen.voice_seed,
        temp_asset_id=asset.id,
    )


async def preview_batch_tts(
    req: BatchTTSPreviewRequest,
    db: Session,
) -> BatchTTSPreviewResponse:
    """Generate TTS previews for multiple scenes with concurrency limit.

    DB writes are serialised after concurrent TTS generation to avoid
    sharing a single SQLAlchemy Session across async tasks.
    """

    async def _generate(idx: int, scene_req: SceneTTSPreviewRequest):
        if req.storyboard_id and not scene_req.storyboard_id:
            scene_req.storyboard_id = req.storyboard_id
        if req.voice_preset_id and not scene_req.voice_preset_id:
            scene_req.voice_preset_id = req.voice_preset_id

        async with _TTS_BATCH_SEMAPHORE:
            return idx, await _generate_scene_tts(scene_req)

    # Phase 1: concurrent TTS generation (no DB)
    gen_tasks = [_generate(i, scene) for i, scene in enumerate(req.scenes)]
    raw_results = await asyncio.gather(*gen_tasks, return_exceptions=True)

    # Phase 2: sequential DB writes
    items: list[BatchTTSPreviewItem] = []
    for i, result in enumerate(raw_results):
        if isinstance(result, Exception):
            from services.video.tts_helpers import tts_cache_key
            from services.video.utils import clean_script_for_tts

            scene_req = req.scenes[i]
            ck = tts_cache_key(
                clean_script_for_tts(scene_req.script) if scene_req.script.strip() else "",
                scene_req.voice_preset_id,
                scene_req.voice_design_prompt,
                scene_req.language,
            )
            logger.warning("[Preview] Batch TTS failed for scene %d: %s", i, result)
            items.append(BatchTTSPreviewItem(scene_index=i, status="failed", cache_key=ck, error=str(result)))
        else:
            idx, gen = result
            asset = _save_audio_asset(db, gen.audio_bytes, gen.cache_key)
            items.append(
                BatchTTSPreviewItem(
                    scene_index=idx,
                    status="cached" if gen.cached else "success",
                    audio_url=asset.url,
                    duration=gen.duration,
                    cache_key=gen.cache_key,
                )
            )

    items.sort(key=lambda x: x.scene_index)
    cached = sum(1 for i in items if i.status == "cached")
    generated = sum(1 for i in items if i.status == "success")
    failed = sum(1 for i in items if i.status == "failed")
    total_dur = sum(i.duration or 0 for i in items)

    return BatchTTSPreviewResponse(
        items=items,
        total_duration=total_dur,
        cached_count=cached,
        generated_count=generated,
        failed_count=failed,
    )
