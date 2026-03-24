"""ControlNet API endpoints."""

import base64

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import DEFAULT_CHARACTER_PRESET, logger
from database import get_db
from models.character import Character
from schemas import (
    ControlNetStatusResponse,
    DeletedKeyResponse,
    IPAdapterStatusResponse,
    PoseListResponse,
    PoseReferenceResponse,
    QualityInfo,
    ReferenceListResponse,
    ReferenceQualityResponse,
    SuggestPoseResponse,
    UploadPhotoReferenceRequest,
    UploadPhotoReferenceResponse,
)
from services.controlnet import (
    IP_ADAPTER_MODELS,
    POSE_MAPPING,
    create_pose_from_image,
    delete_reference_image,
    detect_pose_from_prompt,
    list_reference_images,
    load_pose_reference,
    load_reference_image,
    save_reference_image,
)
from services.ip_adapter import (
    upload_photo_reference,
    validate_reference_quality,
)
from services.sd_client.factory import get_sd_client

router = APIRouter(prefix="/controlnet", tags=["controlnet-admin"])
service_router = APIRouter(prefix="/controlnet", tags=["controlnet"])


class PoseDetectRequest(BaseModel):
    image_b64: str


class PoseDetectResponse(BaseModel):
    pose_image: str | None = None
    success: bool = False
    error: str | None = None


@router.get("/status", response_model=ControlNetStatusResponse)
async def get_controlnet_status():
    """Check ControlNet availability and list models."""
    sd = get_sd_client()
    available = await sd.check_controlnet()
    models = await sd.get_controlnet_models() if available else []
    return {
        "is_available": available,
        "models": models,
        "pose_references": list(POSE_MAPPING.keys()),
    }


@router.get("/poses", response_model=PoseListResponse)
async def list_available_poses():
    """List available pose references."""
    poses = []
    for pose_name, filename in POSE_MAPPING.items():
        poses.append(
            {
                "name": pose_name,
                "filename": filename,
                "is_available": load_pose_reference(pose_name) is not None,
            }
        )
    return {"poses": poses}


@router.get("/pose/{pose_name}", response_model=PoseReferenceResponse)
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
        result = await create_pose_from_image(request.image_b64)
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
        logger.exception("Pose detection failed: %s", e)
        return PoseDetectResponse(
            success=False,
            error="Pose detection failed",
        )


@router.post("/suggest-pose", response_model=SuggestPoseResponse)
async def suggest_pose_for_tags(tags: list[str]):
    """Suggest a pose reference based on prompt tags."""
    pose = detect_pose_from_prompt(", ".join(tags))
    if pose:
        pose_b64 = load_pose_reference(pose)
        return {
            "suggested_pose": pose,
            "is_available": pose_b64 is not None,
            "image_b64": pose_b64,
        }
    return {
        "suggested_pose": None,
        "is_available": False,
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


@router.get("/ip-adapter/status", response_model=IPAdapterStatusResponse)
async def get_ip_adapter_status():
    """Check IP-Adapter availability."""
    sd = get_sd_client()
    available = await sd.check_controlnet()
    models = await sd.get_controlnet_models() if available else []
    ip_models = [m for m in models if "ip-adapter" in m.lower()]
    return {
        "is_available": len(ip_models) > 0,
        "models": ip_models,
        "supported_models": list(IP_ADAPTER_MODELS.keys()),
    }


@service_router.get("/ip-adapter/references", response_model=ReferenceListResponse)
async def list_references(db: Session = Depends(get_db)):
    """List all saved reference images for IP-Adapter with presets from DB/Config."""
    # 1. Get physical files
    refs = list_reference_images(db=db)

    # 2. Get all characters from DB for enrichment (exclude soft-deleted)
    db_chars = {c.name: c for c in db.query(Character).filter(Character.deleted_at.is_(None)).all()}

    # Enrich with preset info
    for ref in refs:
        char_key = ref["character_key"]

        # Priority 1: Database character settings
        if char_key in db_chars:
            db_char = db_chars[char_key]
            ref["preset"] = {
                "weight": db_char.ip_adapter_weight or 0.75,
                "model": db_char.ip_adapter_model or "clip",
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
        logger.exception("Failed to save reference image: %s", e)
        return ReferenceImageResponse(
            character_key=request.character_key,
            success=False,
            error="Failed to save reference image",
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


@service_router.get("/ip-adapter/reference/{character_key}/image")
async def get_reference_image(character_key: str, db: Session = Depends(get_db)):
    """Get a specific reference image as PNG file."""
    from services.controlnet import load_reference_image

    image_b64 = load_reference_image(character_key, db=db)
    if not image_b64:
        raise HTTPException(status_code=404, detail=f"Reference '{character_key}' not found")

    # Decode base64 to bytes
    image_bytes = base64.b64decode(image_b64)

    return Response(content=image_bytes, media_type="image/png")


@router.delete("/ip-adapter/reference/{character_key}", response_model=DeletedKeyResponse)
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
        logger.exception("Failed to upload photo reference: %s", e)
        return UploadPhotoReferenceResponse(
            character_key=request.character_key,
            success=False,
            error="Failed to upload photo reference",
        )
