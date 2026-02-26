"""MusicPreset CRUD, preview generation, and model warmup endpoints."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.media_asset import MediaAsset
from models.music_preset import MusicPreset
from schemas import (
    MusicPresetCreate,
    MusicPresetResponse,
    MusicPresetUpdate,
    MusicPreviewRequest,
)
from services.asset_service import AssetService
from services.storage import get_storage

router = APIRouter(prefix="/music-presets", tags=["music-presets"])


def _preset_to_response(preset: MusicPreset) -> dict:
    """Build response dict with audio_url from eager-loaded relationship."""
    audio_url = preset.audio_asset.url if preset.audio_asset else None
    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "prompt": preset.prompt,
        "duration": preset.duration,
        "seed": preset.seed,
        "audio_url": audio_url,
        "is_system": preset.is_system,
        "created_at": preset.created_at,
    }


@router.get("", response_model=list[MusicPresetResponse])
def list_music_presets(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload

    presets = db.query(MusicPreset).options(joinedload(MusicPreset.audio_asset)).order_by(MusicPreset.id).all()
    return [_preset_to_response(p) for p in presets]


@router.get("/{preset_id}", response_model=MusicPresetResponse)
def get_music_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(MusicPreset).filter(MusicPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Music preset not found")
    return _preset_to_response(preset)


@router.post("", response_model=MusicPresetResponse, status_code=201)
def create_music_preset(body: MusicPresetCreate, db: Session = Depends(get_db)):
    preset = MusicPreset(
        **body.model_dump(exclude_unset=True),
        is_system=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@router.put("/{preset_id}", response_model=MusicPresetResponse)
def update_music_preset(
    preset_id: int,
    body: MusicPresetUpdate,
    db: Session = Depends(get_db),
):
    preset = db.query(MusicPreset).filter(MusicPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Music preset not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(preset, key, value)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@router.delete("/{preset_id}")
def delete_music_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(MusicPreset).filter(MusicPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Music preset not found")
    if preset.audio_asset_id:
        asset = db.get(MediaAsset, preset.audio_asset_id)
        if asset:
            try:
                storage = get_storage()
                storage.delete(asset.storage_key)
            except Exception as e:
                logger.warning(f"[MusicPreset] Failed to delete storage: {e}")
            db.delete(asset)
    db.delete(preset)
    db.commit()
    return {"status": "deleted", "id": preset_id}


@router.post("/preview")
async def preview_music(req: MusicPreviewRequest, db: Session = Depends(get_db)):
    """Generate a preview audio via Audio Server."""
    from services.audio_client import generate_music

    try:
        wav_bytes, _sample_rate, actual_seed = await generate_music(
            prompt=req.prompt,
            duration=req.duration,
            seed=req.seed,
        )

        digest = hashlib.sha1(wav_bytes).hexdigest()[:16]
        file_name = f"music_preview_{digest}.wav"
        storage_key = f"music-presets/previews/{file_name}"

        storage = get_storage()
        storage.save(storage_key, wav_bytes, content_type="audio/wav")

        asset_svc = AssetService(db)
        asset = asset_svc.register_asset(
            file_name=file_name,
            file_type="audio",
            storage_key=storage_key,
            owner_type="music_preview",
            is_temp=True,
            file_size=len(wav_bytes),
            mime_type="audio/wav",
        )

        return {
            "audio_url": asset.url,
            "temp_asset_id": asset.id,
            "seed": actual_seed,
        }
    except Exception as e:
        from services.error_responses import raise_user_error

        raise_user_error("preview_generate", e)


@router.post("/{preset_id}/attach-preview")
def attach_preview_to_preset(
    preset_id: int,
    temp_asset_id: int,
    db: Session = Depends(get_db),
):
    """Attach a previously generated preview audio to a preset."""
    preset = db.query(MusicPreset).filter(MusicPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Music preset not found")

    temp_asset = db.get(MediaAsset, temp_asset_id)
    if not temp_asset:
        raise HTTPException(status_code=404, detail="Temp asset not found")

    temp_asset.is_temp = False
    temp_asset.owner_type = "music_preset"
    temp_asset.owner_id = preset.id
    preset.audio_asset_id = temp_asset.id
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@router.post("/warmup")
async def warmup_musicgen_model():
    """Check Audio Server health (replaces direct model warmup)."""
    from services.audio_client import check_health

    health = await check_health()
    return {"status": health.get("status", "error"), "message": "Audio Server health check", "details": health}
