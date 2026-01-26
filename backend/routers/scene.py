"""Scene generation and validation endpoints."""

from __future__ import annotations

import hashlib
import io

from fastapi import APIRouter, HTTPException
from PIL import Image

from config import API_PUBLIC_URL, IMAGE_DIR, logger
from schemas import ImageStoreRequest, SceneGenerateRequest, SceneValidateRequest
from services.generation import generate_scene_image
from services.image import decode_data_url
from services.utils import scrub_payload
from services.validation import validate_scene_image

router = APIRouter(tags=["scene"])


@router.post("/scene/generate")
async def generate_scene_image_endpoint(request: SceneGenerateRequest):
    # Validate resolution strategy
    if request.width != 512 or request.height != 768:
        logger.warning(
            "⚠️ Non-standard resolution detected: %dx%d. Recommended: 512x768 for optimal Post/Full compatibility.",
            request.width,
            request.height,
        )

    logger.info("📥 [Scene Gen Req] %s", request.model_dump())
    return await generate_scene_image(request)


@router.post("/image/store")
async def store_scene_image(request: ImageStoreRequest):
    try:
        image_bytes = decode_data_url(request.image_b64)
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc
    digest = hashlib.sha1(image_bytes).hexdigest()[:16]
    store_dir = IMAGE_DIR / "stored"
    store_dir.mkdir(parents=True, exist_ok=True)
    filename = f"scene_{digest}.png"
    target = store_dir / filename
    if not target.exists():
        image = image.convert("RGBA")
        image.save(target, format="PNG")
        logger.info("💾 [Image Store] Saved new image: %s", target)
    else:
        logger.info("💾 [Image Store] Image already exists: %s", target)
    return {"url": f"{API_PUBLIC_URL}/outputs/images/stored/{filename}"}


@router.post("/scene/validate_image")
async def validate_scene_image_endpoint(request: SceneValidateRequest):
    logger.info("📥 [Scene Validate Req] %s", scrub_payload(request.model_dump()))
    return validate_scene_image(request)
