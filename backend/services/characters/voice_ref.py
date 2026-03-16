"""Voice Reference Generator — Qwen3-TTS로 캐릭터 보이스 레퍼런스를 생성한다.

GPT-SoVITS가 음색 복제에 사용할 레퍼런스 오디오를 생성하고 MinIO에 저장한다.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import VOICE_REF_SAMPLE_TEXT, logger


async def generate_voice_reference(db: Session, character_id: int) -> dict:
    """캐릭터의 voice_preset으로 레퍼런스 오디오를 생성하고 MinIO에 저장한다."""
    from models.character import Character
    from services.asset_service import AssetService
    from services.audio_client import synthesize_tts
    from services.storage import get_storage
    from services.video.tts_helpers import get_preset_voice_info

    character = db.query(Character).filter(
        Character.id == character_id,
        Character.deleted_at.is_(None),
    ).first()
    if not character:
        raise ValueError(f"캐릭터를 찾을 수 없습니다: {character_id}")

    if not character.voice_preset_id:
        raise ValueError(f"캐릭터 '{character.name}'에 voice preset이 설정되지 않았습니다.")

    voice_design, voice_seed = get_preset_voice_info(character.voice_preset_id)
    if not voice_design:
        raise ValueError(f"Voice preset {character.voice_preset_id}에 voice_design_prompt가 없습니다.")

    logger.info("[VoiceRef] Generating for '%s' (char %d, preset %d)", character.name, character_id, character.voice_preset_id)
    audio_bytes, _sr, duration, _quality = await synthesize_tts(
        text=VOICE_REF_SAMPLE_TEXT,
        instruct=voice_design,
        seed=voice_seed or -1,
        task_id=f"voice_ref_{character_id}",
    )

    # MinIO에 저장
    storage_key = f"characters/{character_id}/voice_refs/default.wav"
    storage = get_storage()
    storage.save(storage_key, audio_bytes, content_type="audio/wav")

    # DB에 에셋 등록
    asset_svc = AssetService(db)
    asset = asset_svc.register_asset(
        file_name=f"voice_ref_{character_id}.wav",
        file_type="audio",
        storage_key=storage_key,
        owner_type="character_voice_ref",
        owner_id=character_id,
        file_size=len(audio_bytes),
        mime_type="audio/wav",
    )

    logger.info("[VoiceRef] Saved: char=%d, asset=%d, dur=%.1fs", character_id, asset.id, duration)
    return {
        "ok": True,
        "character_id": character_id,
        "asset_id": asset.id,
        "duration": duration,
        "storage_key": storage_key,
    }
