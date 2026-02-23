"""VoicePreset CRUD and preview endpoints."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.media_asset import MediaAsset
from models.voice_preset import VoicePreset
from schemas import (
    VoicePresetCreate,
    VoicePresetResponse,
    VoicePresetUpdate,
    VoicePreviewRequest,
)
from services.asset_service import AssetService
from services.storage import get_storage

router = APIRouter(prefix="/voice-presets", tags=["voice-presets"])


def _preset_to_response(preset: VoicePreset, db: Session) -> dict:
    """Build response dict with computed audio_url."""
    audio_url = None
    if preset.audio_asset_id:
        asset = db.get(MediaAsset, preset.audio_asset_id)
        if asset:
            audio_url = asset.url
    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "source_type": preset.source_type,
        "audio_url": audio_url,
        "voice_design_prompt": preset.voice_design_prompt,
        "voice_seed": preset.voice_seed,
        "language": preset.language,
        "sample_text": preset.sample_text,
        "is_system": preset.is_system,
        "created_at": preset.created_at,
    }


@router.get("", response_model=list[VoicePresetResponse])
def list_voice_presets(db: Session = Depends(get_db)):
    presets = db.query(VoicePreset).order_by(VoicePreset.id).all()
    return [_preset_to_response(p, db) for p in presets]


@router.get("/{preset_id}", response_model=VoicePresetResponse)
def get_voice_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")
    return _preset_to_response(preset, db)


@router.post("", response_model=VoicePresetResponse, status_code=201)
def create_voice_preset(body: VoicePresetCreate, db: Session = Depends(get_db)):
    preset = VoicePreset(
        **body.model_dump(exclude_unset=True, exclude={"source_type"}),
        source_type="generated",
        tts_engine="qwen",
        is_system=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset, db)


@router.put("/{preset_id}", response_model=VoicePresetResponse)
def update_voice_preset(
    preset_id: int,
    body: VoicePresetUpdate,
    db: Session = Depends(get_db),
):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(preset, key, value)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset, db)


@router.delete("/{preset_id}")
def delete_voice_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")
    # Clean up MediaAsset
    if preset.audio_asset_id:
        asset = db.get(MediaAsset, preset.audio_asset_id)
        if asset:
            try:
                storage = get_storage()
                storage.delete(asset.storage_key)
            except Exception as e:
                logger.warning(f"[VoicePreset] Failed to delete storage: {e}")
            db.delete(asset)
    db.delete(preset)
    db.commit()
    return {"status": "deleted", "id": preset_id}


@router.post("/preview")
async def preview_voice(req: VoicePreviewRequest, db: Session = Depends(get_db)):
    """Generate a preview audio via Audio Server."""
    from config import TTS_DEFAULT_LANGUAGE
    from services.audio_client import synthesize_tts
    from services.video.tts_helpers import translate_voice_prompt

    try:
        voice_design = translate_voice_prompt(req.voice_design_prompt)
        voice_seed = hash(voice_design) % (2**31)

        audio_bytes, _sr, _duration, _quality = await synthesize_tts(
            text=req.sample_text,
            instruct=voice_design,
            language=req.language or TTS_DEFAULT_LANGUAGE,
            seed=voice_seed,
        )

        digest = hashlib.sha1(audio_bytes).hexdigest()[:16]
        file_name = f"voice_preview_{digest}.wav"
        storage_key = f"voice-presets/previews/{file_name}"

        storage = get_storage()
        storage.save(storage_key, audio_bytes, content_type="audio/wav")

        asset_svc = AssetService(db)
        asset = asset_svc.register_asset(
            file_name=file_name,
            file_type="audio",
            storage_key=storage_key,
            owner_type="voice_preview",
            is_temp=True,
            file_size=len(audio_bytes),
            mime_type="audio/wav",
        )

        return {
            "audio_url": asset.url,
            "temp_asset_id": asset.id,
            "voice_seed": voice_seed,
        }
    except Exception as e:
        logger.error(f"[VoicePreset] Preview generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {e}") from e


@router.post("/{preset_id}/attach-preview")
def attach_preview_to_preset(
    preset_id: int,
    temp_asset_id: int,
    db: Session = Depends(get_db),
):
    """Attach a previously generated preview audio to a preset."""
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")

    temp_asset = db.get(MediaAsset, temp_asset_id)
    if not temp_asset:
        raise HTTPException(status_code=404, detail="Temp asset not found")

    # Move from temp to permanent
    temp_asset.is_temp = False
    temp_asset.owner_type = "voice_preset"
    temp_asset.owner_id = preset.id
    preset.audio_asset_id = temp_asset.id
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset, db)
