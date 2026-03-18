"""TTS preview: single scene + batch generation.

Reuses render-pipeline TTS helpers and cache keys.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from config import (
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
from services.video.tts_helpers import TTS_CONCURRENCY_SEMAPHORE as _TTS_BATCH_SEMAPHORE


@dataclass
class _TtsGenResult:
    """Internal result of TTS generation (no DB write)."""

    audio_bytes: bytes
    duration: float
    cache_key: str
    cached: bool
    voice_seed: int
    voice_design: str | None


async def _generate_scene_tts(req: SceneTTSPreviewRequest) -> _TtsGenResult:
    """Generate TTS audio without any DB writes (pure I/O + cache)."""
    from services.video.tts_helpers import (
        TtsAudioResult,
        generate_tts_audio,
        get_speaker_voice_preset,
    )
    from services.video.utils import has_speakable_content

    script = req.script.strip()
    if not script or not has_speakable_content(script):
        raise ValueError("스크립트에 TTS로 변환할 내용이 없습니다.")

    # Resolve voice preset at call site (core function requires pre-resolved id)
    voice_preset_id = req.voice_preset_id
    if not voice_preset_id and req.storyboard_id:
        voice_preset_id = get_speaker_voice_preset(req.storyboard_id, req.speaker)

    result: TtsAudioResult = await generate_tts_audio(
        script=script,
        speaker=req.speaker,
        voice_preset_id=voice_preset_id,
        scene_voice_design=req.voice_design_prompt,
        global_voice_design=None,
        scene_emotion=req.scene_emotion or "",
        language=req.language,
        force_regenerate=req.force_regenerate,
        max_retries=0,
    )

    return _TtsGenResult(
        audio_bytes=result.audio_bytes,
        duration=result.duration,
        cache_key=result.cache_key,
        cached=result.cached,
        voice_seed=result.voice_seed,
        voice_design=result.voice_design,
    )


def _save_audio_asset(db: Session, audio_bytes: bytes, cache_key: str):
    """Save audio bytes to storage and register as temp asset.

    If an asset with the same storage_key already exists, return it
    (avoids UniqueViolation on force_regenerate with identical audio).
    """
    from models.media_asset import MediaAsset

    digest = hashlib.sha256(audio_bytes).hexdigest()[:16]
    file_name = f"tts_preview_{digest}.wav"
    storage_key = f"previews/tts/{file_name}"

    # Return existing asset if storage_key already registered
    existing = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()
    if existing:
        return existing

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


# ── Public API ──────────────────────────────────────────


async def preview_scene_tts(
    req: SceneTTSPreviewRequest,
    db: Session,
) -> SceneTTSPreviewResponse:
    """Generate TTS preview for a single scene. Cache-compatible with render pipeline.

    scene_db_id 제공 시 Scene.tts_asset_id를 즉시 업데이트하여 렌더에 반영되도록 보장한다.
    """
    from models.scene import Scene

    gen = await _generate_scene_tts(req)
    asset = _save_audio_asset(db, gen.audio_bytes, gen.cache_key)

    if req.scene_db_id is not None:
        scene = db.get(Scene, req.scene_db_id)
        if scene and not scene.deleted_at:
            asset.is_temp = False
            scene.tts_asset_id = asset.id
            db.commit()
            logger.info("[Preview] Scene %d tts_asset_id → %d (permanent)", req.scene_db_id, asset.id)

    return SceneTTSPreviewResponse(
        audio_url=asset.url,
        duration=gen.duration,
        cache_key=gen.cache_key,
        cached=gen.cached,
        voice_seed=gen.voice_seed,
        voice_design=gen.voice_design,
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
                speaker=scene_req.speaker,
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
                    temp_asset_id=asset.id,
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
