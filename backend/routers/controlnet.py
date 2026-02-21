"""ControlNet API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import DEFAULT_CHARACTER_PRESET, logger
from database import get_db
from models.character import Character
from models.media_asset import MediaAsset
from schemas import (
    MultiReferenceRequest,
    MultiReferenceResponse,
    MultiReferenceSaved,
    QualityInfo,
    ReferenceQualityResponse,
    UploadPhotoReferenceRequest,
    UploadPhotoReferenceResponse,
)
from services.controlnet import (
    IP_ADAPTER_MODELS,
    POSE_MAPPING,
    check_controlnet_available,
    create_pose_from_image,
    delete_reference_image,
    detect_pose_from_prompt,
    get_controlnet_models,
    list_reference_images,
    load_pose_reference,
    load_reference_image,
    save_reference_image,
)
from services.ip_adapter import (
    upload_photo_reference,
    validate_reference_quality,
)

router = APIRouter(prefix="/controlnet", tags=["controlnet"])


class PoseDetectRequest(BaseModel):
    image_b64: str


class PoseDetectResponse(BaseModel):
    pose_image: str | None = None
    success: bool = False
    error: str | None = None


@router.get("/status")
async def get_controlnet_status():
    """Check ControlNet availability and list models."""
    available = check_controlnet_available()
    models = get_controlnet_models() if available else []
    return {
        "available": available,
        "models": models,
        "pose_references": list(POSE_MAPPING.keys()),
    }


@router.get("/poses")
async def list_available_poses():
    """List available pose references."""
    poses = []
    for pose_name, filename in POSE_MAPPING.items():
        poses.append(
            {
                "name": pose_name,
                "filename": filename,
                "available": load_pose_reference(pose_name) is not None,
            }
        )
    return {"poses": poses}


@router.get("/pose/{pose_name}")
async def get_pose_reference(pose_name: str):
    """Get a specific pose reference image."""
    pose_b64 = load_pose_reference(pose_name)
    if not pose_b64:
        raise HTTPException(status_code=404, detail=f"Pose '{pose_name}' not found")
    return {
        "pose_name": pose_name,
        "image_b64": pose_b64,
    }


@router.post("/detect-pose", response_model=PoseDetectResponse)
async def detect_pose(request: PoseDetectRequest):
    """Extract pose skeleton from an image."""
    try:
        result = create_pose_from_image(request.image_b64)
        images = result.get("images", [])
        if images:
            return PoseDetectResponse(
                pose_image=images[0],
                success=True,
            )
        return PoseDetectResponse(
            success=False,
            error="No pose detected",
        )
    except Exception as e:
        logger.exception("Pose detection failed")
        return PoseDetectResponse(
            success=False,
            error=str(e),
        )


@router.post("/suggest-pose")
async def suggest_pose_for_tags(tags: list[str]):
    """Suggest a pose reference based on prompt tags."""
    pose = detect_pose_from_prompt(tags)
    if pose:
        pose_b64 = load_pose_reference(pose)
        return {
            "suggested_pose": pose,
            "available": pose_b64 is not None,
            "image_b64": pose_b64,
        }
    return {
        "suggested_pose": None,
        "available": False,
        "image_b64": None,
    }


# ============================================================
# IP-Adapter Endpoints (Character Consistency)
# ============================================================


class ReferenceImageRequest(BaseModel):
    character_key: str
    image_b64: str


class ReferenceImageResponse(BaseModel):
    character_key: str
    filename: str | None = None
    image_b64: str | None = None
    success: bool = False
    error: str | None = None


@router.get("/ip-adapter/status")
async def get_ip_adapter_status():
    """Check IP-Adapter availability."""
    available = check_controlnet_available()
    models = get_controlnet_models() if available else []
    ip_models = [m for m in models if "ip-adapter" in m.lower()]
    return {
        "available": len(ip_models) > 0,
        "models": ip_models,
        "supported_models": list(IP_ADAPTER_MODELS.keys()),
    }


@router.get("/ip-adapter/references")
async def list_references(db: Session = Depends(get_db)):
    """List all saved reference images for IP-Adapter with presets from DB/Config."""
    # 1. Get physical files
    refs = list_reference_images(db=db)

    # 2. Get all characters from DB for enrichment
    db_chars = {c.name: c for c in db.query(Character).all()}

    # Enrich with preset info
    for ref in refs:
        char_key = ref["character_key"]

        # Priority 1: Database character settings
        if char_key in db_chars:
            db_char = db_chars[char_key]
            ref["preset"] = {
                "weight": db_char.ip_adapter_weight or 0.75,
                "model": db_char.ip_adapter_model or "clip_face",
                "description": db_char.description or f"DB Character: {char_key}",
            }
        else:
            # Priority 2: Static config presets
            ref["preset"] = DEFAULT_CHARACTER_PRESET

    return {"references": refs}


@router.post("/ip-adapter/reference", response_model=ReferenceImageResponse)
async def upload_reference(request: ReferenceImageRequest):
    """Upload a reference image for IP-Adapter character consistency."""
    try:
        filename = save_reference_image(request.character_key, request.image_b64)
        return ReferenceImageResponse(
            character_key=request.character_key,
            filename=filename,
            success=True,
        )
    except Exception as e:
        logger.exception("Failed to save reference image")
        return ReferenceImageResponse(
            character_key=request.character_key,
            success=False,
            error=str(e),
        )


@router.get("/ip-adapter/reference/{character_key}", response_model=ReferenceImageResponse)
async def get_reference(character_key: str):
    """Get a specific reference image as JSON with base64."""
    image_b64 = load_reference_image(character_key)
    if not image_b64:
        return ReferenceImageResponse(
            character_key=character_key,
            success=False,
            error=f"Reference '{character_key}' not found",
        )
    return ReferenceImageResponse(
        character_key=character_key,
        filename=f"{character_key}.png",
        image_b64=image_b64,
        success=True,
    )


@router.get("/ip-adapter/reference/{character_key}/image")
async def get_reference_image(character_key: str, db: Session = Depends(get_db)):
    """Get a specific reference image as PNG file."""
    import base64

    from services.controlnet import load_reference_image

    image_b64 = load_reference_image(character_key, db=db)
    if not image_b64:
        raise HTTPException(status_code=404, detail=f"Reference '{character_key}' not found")

    # Decode base64 to bytes
    image_bytes = base64.b64decode(image_b64)

    return Response(content=image_bytes, media_type="image/png")


@router.delete("/ip-adapter/reference/{character_key}")
async def remove_reference(character_key: str):
    """Delete a reference image."""
    deleted = delete_reference_image(character_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Reference '{character_key}' not found")
    return {"deleted": character_key}


@router.get(
    "/ip-adapter/reference/{character_key}/quality",
    response_model=ReferenceQualityResponse,
)
async def check_reference_quality(character_key: str, db: Session = Depends(get_db)):
    """Check quality of a saved reference image (face detection, resolution, etc.)."""
    image_b64 = load_reference_image(character_key, db=db)
    if not image_b64:
        raise HTTPException(status_code=404, detail=f"Reference '{character_key}' not found")

    report = validate_reference_quality(image_b64)
    return ReferenceQualityResponse(
        character_key=character_key,
        valid=report.valid,
        face_detected=report.face_detected,
        face_count=report.face_count,
        face_size_ratio=report.face_size_ratio,
        resolution_ok=report.resolution_ok,
        width=report.width,
        height=report.height,
        warnings=report.warnings,
    )


@router.post(
    "/ip-adapter/reference/upload-photo",
    response_model=UploadPhotoReferenceResponse,
)
async def upload_photo_ref(request: UploadPhotoReferenceRequest, db: Session = Depends(get_db)):
    """Upload a real photo as reference (auto face-crop + resize to 512x512)."""
    try:
        filename, quality = upload_photo_reference(
            request.character_key,
            request.image_b64,
            db=db,
        )
        return UploadPhotoReferenceResponse(
            character_key=request.character_key,
            filename=filename,
            success=True,
            quality=QualityInfo(
                valid=quality.valid,
                face_detected=quality.face_detected,
                face_count=quality.face_count,
                face_size_ratio=quality.face_size_ratio,
                warnings=quality.warnings,
            ),
        )
    except Exception as e:
        logger.exception("Failed to upload photo reference")
        return UploadPhotoReferenceResponse(
            character_key=request.character_key,
            success=False,
            error=str(e),
        )


@router.post("/ip-adapter/reference/multi", response_model=MultiReferenceResponse)
async def save_multi_references(request: MultiReferenceRequest, db: Session = Depends(get_db)):
    """Save multi-angle reference images for a character."""
    char = db.query(Character).filter(Character.name == request.character_key).first()
    if not char:
        raise HTTPException(status_code=404, detail=f"Character '{request.character_key}' not found")

    saved_refs: list[MultiReferenceSaved] = []
    for ref in request.references:
        # Save each angle as a separate reference file
        filename = save_reference_image(f"{request.character_key}_{ref.angle}", ref.image_b64, db=db)
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.storage_key == f"shared/references/{request.character_key}_{ref.angle}.png")
            .first()
        )
        saved_refs.append(MultiReferenceSaved(
            angle=ref.angle,
            asset_id=asset.id if asset else None,
            filename=filename,
        ))

    # Update character.reference_images JSONB
    char.reference_images = [
        {"angle": r.angle, "asset_id": r.asset_id} for r in saved_refs if r.asset_id
    ]
    db.commit()

    return MultiReferenceResponse(character_key=request.character_key, references=saved_refs)
