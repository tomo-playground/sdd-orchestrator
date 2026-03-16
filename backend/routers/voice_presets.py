"""VoicePreset CRUD and preview endpoints."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.group import Group
from models.media_asset import MediaAsset
from models.voice_preset import VoicePreset
from schemas import (
    StatusResponse,
    VoicePresetCreate,
    VoicePresetResponse,
    VoicePresetUpdate,
    VoicePreviewRequest,
)
from services.asset_service import AssetService
from services.storage import get_storage

service_router = APIRouter(prefix="/voice-presets", tags=["voice-presets"])
admin_router = APIRouter(prefix="/voice-presets", tags=["voice-presets-admin"])


def _compute_voice_seed(voice_design_prompt: str | None) -> int | None:
    """Compute a deterministic voice_seed from voice_design_prompt.

    Backend is SSOT for seed — Frontend may send it, but Backend always
    ensures a seed exists when voice_design_prompt is present.
    """
    if not voice_design_prompt:
        return None
    from services.video.tts_helpers import translate_voice_prompt

    translated = translate_voice_prompt(voice_design_prompt)
    return hash(translated) % (2**31)


def _preset_to_response(preset: VoicePreset) -> dict:
    """Build response dict with audio_url from eager-loaded relationship."""

    audio_url = preset.audio_asset.url if preset.audio_asset else None
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


@service_router.get("", response_model=list[VoicePresetResponse])
def list_voice_presets(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload

    presets = db.query(VoicePreset).options(joinedload(VoicePreset.audio_asset)).order_by(VoicePreset.id).all()
    return [_preset_to_response(p) for p in presets]


@service_router.get("/{preset_id}", response_model=VoicePresetResponse)
def get_voice_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")
    return _preset_to_response(preset)


@admin_router.post("", response_model=VoicePresetResponse, status_code=201)
def create_voice_preset(body: VoicePresetCreate, db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True, exclude={"source_type"})
    # Auto-compute voice_seed if not provided
    if not data.get("voice_seed") and data.get("voice_design_prompt"):
        data["voice_seed"] = _compute_voice_seed(data["voice_design_prompt"])
    preset = VoicePreset(
        **data,
        source_type="generated",
        tts_engine="qwen",
        is_system=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@admin_router.put("/{preset_id}", response_model=VoicePresetResponse)
def update_voice_preset(
    preset_id: int,
    body: VoicePresetUpdate,
    db: Session = Depends(get_db),
):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")
    data = body.model_dump(exclude_unset=True)
    # Re-compute voice_seed when voice_design_prompt changes
    if "voice_design_prompt" in data and "voice_seed" not in data:
        data["voice_seed"] = _compute_voice_seed(data["voice_design_prompt"])
    for key, value in data.items():
        setattr(preset, key, value)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@admin_router.delete("/{preset_id}", response_model=StatusResponse)
def delete_voice_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Voice preset not found")

    # FK reference check: active groups using this preset
    ref_count = db.query(Group).filter(
        Group.narrator_voice_preset_id == preset_id,
        Group.deleted_at.is_(None),
    ).count()
    if ref_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Voice preset is used by {ref_count} active group(s)",
        )

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


@admin_router.post("/preview")
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

        digest = hashlib.sha256(audio_bytes).hexdigest()[:16]
        file_name = f"voice_preview_{digest}.wav"
        storage_key = f"voice-presets/previews/{file_name}"

        storage = get_storage()
        storage.save(storage_key, audio_bytes, content_type="audio/wav")

        # 동일 storage_key의 기존 asset이 있으면 재사용 (재생성 시 unique 위반 방지)
        from models.media_asset import MediaAsset

        existing = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()
        if existing:
            existing.file_size = len(audio_bytes)
            existing.checksum = AssetService.compute_checksum(audio_bytes)
            db.commit()
            asset = existing
        else:
            asset_svc = AssetService(db)
            asset = asset_svc.register_asset(
                file_name=file_name,
                file_type="audio",
                storage_key=storage_key,
                owner_type="voice_preview",
                is_temp=True,
                file_size=len(audio_bytes),
                mime_type="audio/wav",
                checksum=AssetService.compute_checksum(audio_bytes),
            )

        return {
            "audio_url": asset.url,
            "temp_asset_id": asset.id,
            "voice_seed": voice_seed,
        }
    except Exception as e:
        from services.error_responses import raise_user_error

        raise_user_error("preview_generate", e)


@admin_router.post("/{preset_id}/attach-preview")
def attach_preview_to_preset(
    preset_id: int,
    temp_asset_id: int,
    voice_seed: int | None = None,
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
    # Update voice_seed if provided, or auto-compute if still None
    if voice_seed is not None:
        preset.voice_seed = voice_seed
    elif not preset.voice_seed and preset.voice_design_prompt:
        preset.voice_seed = _compute_voice_seed(preset.voice_design_prompt)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)
