"""ControlNet API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import logger
from services.controlnet import (
    check_controlnet_available,
    get_controlnet_models,
    load_pose_reference,
    detect_pose_from_prompt,
    create_pose_from_image,
    save_reference_image,
    load_reference_image,
    list_reference_images,
    delete_reference_image,
    POSE_MAPPING,
    IP_ADAPTER_MODELS,
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
        poses.append({
            "name": pose_name,
            "filename": filename,
            "available": load_pose_reference(pose_name) is not None,
        })
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
async def list_references():
    """List all saved reference images for IP-Adapter."""
    refs = list_reference_images()
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
    """Get a specific reference image."""
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


@router.delete("/ip-adapter/reference/{character_key}")
async def remove_reference(character_key: str):
    """Delete a reference image."""
    deleted = delete_reference_image(character_key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Reference '{character_key}' not found")
    return {"deleted": character_key}
