"""TTS Prebuild service: Autopilot 파이프라인 render 전 TTS 사전 생성.

preview_tts.py의 _generate_scene_tts 로직을 재사용하되,
결과를 Scene.tts_asset_id에 영구 저장하는 것이 핵심 차이점.
"""

from __future__ import annotations

import asyncio
import hashlib

from sqlalchemy.orm import Session

from config import (
    TTS_CACHE_DIR,
    TTS_DEFAULT_SEED,
    TTS_MAX_NEW_TOKENS_BASE,
    TTS_MAX_NEW_TOKENS_CAP,
    TTS_MAX_NEW_TOKENS_PER_CHAR,
    TTS_PREBUILD_CONCURRENCY,
    TTS_REPETITION_PENALTY,
    TTS_TEMPERATURE,
    TTS_TOP_P,
    logger,
)
from schemas import TtsPrebuildRequest, TtsPrebuildResponse, TtsPrebuildResult

_PREBUILD_SEMAPHORE = asyncio.Semaphore(TTS_PREBUILD_CONCURRENCY)


async def _generate_audio(
    script: str,
    speaker: str,
    voice_design_prompt: str | None,
    storyboard_id: int,
) -> tuple[bytes, float]:
    """TTS 오디오 바이트와 재생 시간을 반환한다.

    캐시 hit 시 캐시에서 읽고, miss 시 Audio Server에 요청 후 캐시에 저장한다.
    """
    from services.audio_client import synthesize_tts
    from services.video.tts_helpers import (
        get_preset_voice_info,
        get_speaker_voice_preset,
        translate_voice_prompt,
        tts_cache_key,
    )
    from services.video.utils import clean_script_for_tts, has_speakable_content

    cleaned = clean_script_for_tts(script.strip())
    if not cleaned or not has_speakable_content(cleaned):
        raise ValueError("스크립트에 TTS로 변환할 내용이 없습니다.")

    voice_preset_id = get_speaker_voice_preset(storyboard_id, speaker)
    voice_design = voice_design_prompt
    voice_seed: int | None = None

    if voice_preset_id:
        preset_prompt, preset_seed = get_preset_voice_info(voice_preset_id)
        if not voice_design and preset_prompt:
            voice_design = preset_prompt
        if preset_seed is not None:
            voice_seed = preset_seed

    if voice_seed is None:
        voice_seed = TTS_DEFAULT_SEED

    cache_key = tts_cache_key(cleaned, voice_preset_id, voice_design, "korean", speaker=speaker)
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"

    if voice_design:
        voice_design = translate_voice_prompt(voice_design)

    if cache_path.exists():
        audio_bytes = cache_path.read_bytes()
        duration = _wav_duration(audio_bytes)
        logger.info("[TtsPrebuild] Cache hit: %s (%.1fs)", cache_key, duration)
        return audio_bytes, duration

    max_tokens = min(
        TTS_MAX_NEW_TOKENS_BASE + len(cleaned) * TTS_MAX_NEW_TOKENS_PER_CHAR,
        TTS_MAX_NEW_TOKENS_CAP,
    )

    audio_bytes, _sr, duration, _quality = await synthesize_tts(
        text=cleaned,
        instruct=voice_design or "",
        language="korean",
        seed=voice_seed,
        temperature=TTS_TEMPERATURE,
        top_p=TTS_TOP_P,
        repetition_penalty=TTS_REPETITION_PENALTY,
        max_new_tokens=max_tokens,
    )

    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio_bytes)
    logger.info("[TtsPrebuild] Generated + cached: %s (%.1fs)", cache_key, duration)

    return audio_bytes, duration


def _wav_duration(wav_bytes: bytes) -> float:
    """WAV 바이트에서 재생 시간(초)을 계산한다."""
    import io
    import wave

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate if rate > 0 else 0.0


def _save_tts_asset(db: Session, audio_bytes: bytes, scene_db_id: int) -> int:
    """오디오 바이트를 스토리지에 저장하고 MediaAsset ID를 반환한다.

    동일 내용의 에셋이 이미 있으면 기존 ID를 반환한다 (중복 저장 방지).
    is_temp=False로 저장해 GC에 의해 삭제되지 않도록 한다.
    """
    from models.media_asset import MediaAsset
    from services.asset_service import AssetService
    from services.storage import get_storage

    digest = hashlib.sha256(audio_bytes).hexdigest()[:16]
    file_name = f"tts_scene_{scene_db_id}_{digest}.wav"
    storage_key = f"storyboard/tts/{file_name}"

    existing = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()
    if existing:
        return existing.id

    storage = get_storage()
    storage.save(storage_key, audio_bytes, content_type="audio/wav")

    asset_svc = AssetService(db)
    asset = asset_svc.register_asset(
        file_name=file_name,
        file_type="audio",
        storage_key=storage_key,
        owner_type="scene",
        owner_id=scene_db_id,
        is_temp=False,
        file_size=len(audio_bytes),
        mime_type="audio/wav",
        checksum=AssetService.compute_checksum(audio_bytes),
    )
    return asset.id


def _update_scene_tts_asset(db: Session, scene_db_id: int, asset_id: int) -> None:
    """Scene.tts_asset_id를 업데이트한다."""
    from models.scene import Scene

    db.query(Scene).filter(Scene.id == scene_db_id, Scene.deleted_at.is_(None)).update({"tts_asset_id": asset_id})
    db.commit()


async def _prebuild_one(
    storyboard_id: int,
    scene_db_id: int,
    script: str,
    speaker: str,
    voice_design_prompt: str | None,
) -> tuple[bytes, float]:
    """세마포어로 동시성을 제한하며 단일 씬 TTS를 생성한다."""
    async with _PREBUILD_SEMAPHORE:
        return await _generate_audio(script, speaker, voice_design_prompt, storyboard_id)


async def prebuild_tts_for_scenes(
    request: TtsPrebuildRequest,
    db: Session,
) -> TtsPrebuildResponse:
    """스토리보드의 씬 목록에 대해 TTS를 사전 생성한다.

    - tts_asset_id가 유효한 씬 → 스킵
    - 생성 성공 → Scene.tts_asset_id 업데이트, status="prebuilt"
    - 생성 실패 → 전체 실패로 전파하지 않고 status="failed" 기록
    """
    results: list[TtsPrebuildResult] = []

    # Phase 1: 스킵 대상 분리 + 생성 태스크 준비
    skip_ids: set[int] = set()
    gen_items = []

    for item in request.scenes:
        if item.tts_asset_id is not None:
            from models.media_asset import MediaAsset

            asset = db.get(MediaAsset, item.tts_asset_id)
            if asset is not None and not asset.deleted_at:
                skip_ids.add(item.scene_db_id)
                continue
        gen_items.append(item)

    # Phase 2: 동시 TTS 생성 (DB 없이)
    gen_tasks = [
        _prebuild_one(
            request.storyboard_id,
            item.scene_db_id,
            item.script,
            item.speaker,
            item.voice_design_prompt,
        )
        for item in gen_items
    ]

    db.commit()  # Release DB connection before TTS calls (connection pool 반납, 세션 유지)
    raw = await asyncio.gather(*gen_tasks, return_exceptions=True)

    # Phase 3: 결과 처리 (DB 순차 쓰기)
    for item in request.scenes:
        if item.scene_db_id in skip_ids:
            results.append(
                TtsPrebuildResult(
                    scene_db_id=item.scene_db_id,
                    tts_asset_id=item.tts_asset_id,
                    status="skipped",
                )
            )
            continue

    gen_index = 0
    for item in gen_items:
        outcome = raw[gen_index]
        gen_index += 1

        if isinstance(outcome, Exception):
            logger.warning("[TtsPrebuild] Scene %d failed: %s", item.scene_db_id, outcome)
            results.append(
                TtsPrebuildResult(
                    scene_db_id=item.scene_db_id,
                    tts_asset_id=None,
                    status="failed",
                    error=str(outcome),
                )
            )
            continue

        audio_bytes, duration = outcome
        try:
            asset_id = _save_tts_asset(db, audio_bytes, item.scene_db_id)
            _update_scene_tts_asset(db, item.scene_db_id, asset_id)
            results.append(
                TtsPrebuildResult(
                    scene_db_id=item.scene_db_id,
                    tts_asset_id=asset_id,
                    status="prebuilt",
                    duration=duration,
                )
            )
        except Exception as exc:
            logger.warning("[TtsPrebuild] DB write failed for scene %d: %s", item.scene_db_id, exc)
            results.append(
                TtsPrebuildResult(
                    scene_db_id=item.scene_db_id,
                    tts_asset_id=None,
                    status="failed",
                    error=str(exc),
                )
            )

    prebuilt = sum(1 for r in results if r.status == "prebuilt")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")

    logger.info(
        "[TtsPrebuild] storyboard=%d prebuilt=%d skipped=%d failed=%d",
        request.storyboard_id,
        prebuilt,
        skipped,
        failed,
    )

    return TtsPrebuildResponse(results=results, prebuilt=prebuilt, skipped=skipped, failed=failed)
