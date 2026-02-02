"""VoicePreset CRUD, preview, and upload endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import (
    VOICE_PRESET_ALLOWED_FORMATS,
    VOICE_PRESET_MAX_DURATION,
    VOICE_PRESET_MAX_FILE_SIZE,
    VOICE_PRESET_MIN_DURATION,
    logger,
)
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
        "project_id": preset.project_id,
        "source_type": preset.source_type,
        "audio_url": audio_url,
        "voice_design_prompt": preset.voice_design_prompt,
        "language": preset.language,
        "sample_text": preset.sample_text,
        "is_system": preset.is_system,
        "created_at": preset.created_at,
    }


@router.get("", response_model=list[VoicePresetResponse])
def list_voice_presets(
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(VoicePreset)
    if project_id is not None:
        query = query.filter(
            (VoicePreset.project_id == project_id) | (VoicePreset.project_id.is_(None))
        )
    else:
        query = query.filter(VoicePreset.project_id.is_(None))
    presets = query.order_by(VoicePreset.id).all()
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
        **body.model_dump(exclude_unset=True),
        tts_engine="qwen",
        is_system=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset, db)


@router.put("/{preset_id}", response_model=VoicePresetResponse)
def update_voice_preset(
    preset_id: int, body: VoicePresetUpdate, db: Session = Depends(get_db),
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
    """Generate a preview audio using VoiceDesign model."""
    from services.video.scene_processing import (
        TTS_DEFAULT_LANGUAGE,
        _translate_voice_prompt,
        get_qwen_model_async,
    )

    try:
        voice_design = _translate_voice_prompt(req.voice_design_prompt)
        model = await get_qwen_model_async("voice_design")

        loop = asyncio.get_event_loop()

        def _generate():
            import soundfile as sf
            wavs, sr = model.generate_voice_design(
                text=req.sample_text,
                instruct=voice_design,
                language=req.language or TTS_DEFAULT_LANGUAGE,
            )
            buf = io.BytesIO()
            sf.write(buf, wavs[0], sr, format="WAV")
            return buf.getvalue()

        audio_bytes = await loop.run_in_executor(None, _generate)

        # Register as temp MediaAsset (will be GC'd after 24h)
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

        return {"audio_url": asset.url, "temp_asset_id": asset.id}
    except Exception as e:
        logger.error(f"[VoicePreset] Preview generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {e}")


@router.post("/upload", response_model=VoicePresetResponse, status_code=201)
async def upload_voice_preset(
    name: str = Form(...),
    file: UploadFile = File(...),
    project_id: int | None = Form(None),
    description: str | None = Form(None),
    language: str = Form("korean"),
    db: Session = Depends(get_db),
):
    """Upload a custom voice audio file as a preset."""
    # Validate file extension
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in VOICE_PRESET_ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Allowed: {', '.join(VOICE_PRESET_ALLOWED_FORMATS)}",
        )

    # Read and validate file size
    audio_bytes = await file.read()
    if len(audio_bytes) > VOICE_PRESET_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(audio_bytes)} bytes (max {VOICE_PRESET_MAX_FILE_SIZE})",
        )

    # Validate audio duration
    try:
        import soundfile as sf
        buf = io.BytesIO(audio_bytes)
        info = sf.info(buf)
        duration = info.duration
        if duration < VOICE_PRESET_MIN_DURATION:
            raise HTTPException(
                status_code=400,
                detail=f"Audio too short: {duration:.1f}s (min {VOICE_PRESET_MIN_DURATION}s)",
            )
        if duration > VOICE_PRESET_MAX_DURATION:
            raise HTTPException(
                status_code=400,
                detail=f"Audio too long: {duration:.1f}s (max {VOICE_PRESET_MAX_DURATION}s)",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[VoicePreset] Duration check failed (allowing): {e}")

    # Create preset first to get ID
    preset = VoicePreset(
        name=name,
        description=description,
        project_id=project_id,
        source_type="uploaded",
        tts_engine="qwen",
        language=language,
        is_system=False,
    )
    db.add(preset)
    db.flush()

    # Upload to storage
    digest = hashlib.sha1(audio_bytes).hexdigest()[:16]
    file_name = f"voice_{preset.id}_{digest}.{ext}"
    storage_key = f"voice-presets/{preset.id}/{file_name}"

    storage = get_storage()
    storage.save(storage_key, audio_bytes, content_type=file.content_type or f"audio/{ext}")

    # Register MediaAsset
    asset_svc = AssetService(db)
    asset = asset_svc.register_asset(
        file_name=file_name,
        file_type="audio",
        storage_key=storage_key,
        owner_type="voice_preset",
        owner_id=preset.id,
        file_size=len(audio_bytes),
        mime_type=file.content_type or f"audio/{ext}",
    )

    preset.audio_asset_id = asset.id
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset, db)


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
