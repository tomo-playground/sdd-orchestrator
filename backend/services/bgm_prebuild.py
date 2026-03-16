"""BGM Prebuild service: Stage 단계에서 BGM을 사전 생성.

builder.py의 _prepare_auto_bgm() + _cache_bgm_asset() 로직을
VideoBuilder 의존성 없이 독립 함수로 추출.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import MUSICGEN_MAX_DURATION, logger
from schemas import BgmPrebuildResponse


async def prebuild_bgm(
    storyboard_id: int,
    bgm_prompt: str | None,
    db: Session,
) -> BgmPrebuildResponse:
    """BGM 사전 생성 서비스.

    3-Phase 패턴:
    1. DB 조회 + 캐시 체크 + 프롬프트 결정
    2. DB close → 외부 호출 (generate_music)
    3. 결과 저장
    """
    from models.media_asset import MediaAsset
    from models.storyboard import Storyboard

    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not storyboard:
        return BgmPrebuildResponse(status="failed", error="Storyboard not found")

    # Phase 1: 캐시 체크
    if storyboard.bgm_audio_asset_id:
        asset = db.get(MediaAsset, storyboard.bgm_audio_asset_id)
        if asset:
            return BgmPrebuildResponse(
                status="skipped",
                bgm_audio_asset_id=asset.id,
            )

    # Phase 1: 프롬프트 결정 (요청 > DB)
    prompt = bgm_prompt or storyboard.bgm_prompt
    if not prompt:
        return BgmPrebuildResponse(status="no_prompt")

    # Phase 2: DB 커넥션 반납 후 외부 호출 (MusicGen ~60초, DB pool 고갈 방지)
    db.close()
    try:
        wav_bytes = await _generate_bgm(prompt)
    except Exception as exc:
        logger.warning("[BgmPrebuild] Music generation failed: %s", exc)
        return BgmPrebuildResponse(status="failed", error=str(exc))

    # Phase 3: 새 세션으로 에셋 저장 + 스토리보드 연결
    from database import SessionLocal  # noqa: PLC0415

    phase3_db = SessionLocal()
    try:
        asset_id = _save_bgm_asset(phase3_db, storyboard_id, wav_bytes)
        _link_to_storyboard(phase3_db, storyboard_id, asset_id)
        return BgmPrebuildResponse(status="prebuilt", bgm_audio_asset_id=asset_id)
    except Exception as exc:
        phase3_db.rollback()
        logger.warning("[BgmPrebuild] DB write failed: %s", exc)
        return BgmPrebuildResponse(status="failed", error=str(exc))
    finally:
        phase3_db.close()


async def _generate_bgm(prompt: str) -> bytes:
    """Audio Server에서 BGM을 생성한다."""
    from services.audio_client import generate_music

    duration = min(30.0, MUSICGEN_MAX_DURATION)
    wav_bytes, _, _ = await generate_music(prompt=prompt, duration=duration, seed=-1)
    logger.info("[BgmPrebuild] Generated BGM (%d bytes)", len(wav_bytes))
    return wav_bytes


def _save_bgm_asset(db: Session, storyboard_id: int, wav_bytes: bytes) -> int:
    """BGM 바이트를 스토리지에 저장하고 MediaAsset ID를 반환한다."""
    from models.media_asset import MediaAsset
    from services.asset_service import AssetService
    from services.storage import get_storage

    storage_key = f"storyboard/{storyboard_id}/bgm_auto.wav"

    # 동일 키의 기존 에셋 재사용
    existing = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()
    if existing:
        storage = get_storage()
        storage.save(storage_key, wav_bytes, content_type="audio/wav")
        existing.file_size = len(wav_bytes)
        existing.checksum = AssetService.compute_checksum(wav_bytes)
        db.commit()
        return existing.id

    storage = get_storage()
    storage.save(storage_key, wav_bytes, content_type="audio/wav")

    asset_svc = AssetService(db)
    asset = asset_svc.register_asset(
        file_name="bgm_auto.wav",
        file_type="audio",
        storage_key=storage_key,
        owner_type="storyboard",
        owner_id=storyboard_id,
        is_temp=False,
        file_size=len(wav_bytes),
        mime_type="audio/wav",
        checksum=AssetService.compute_checksum(wav_bytes),
    )
    return asset.id


def _link_to_storyboard(db: Session, storyboard_id: int, asset_id: int) -> None:
    """Storyboard.bgm_audio_asset_id를 업데이트한다."""
    from models.storyboard import Storyboard

    db.query(Storyboard).filter(
        Storyboard.id == storyboard_id,
        Storyboard.deleted_at.is_(None),
    ).update({"bgm_audio_asset_id": asset_id})
    db.commit()
