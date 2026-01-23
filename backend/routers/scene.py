"""Scene generation and validation endpoints."""

from __future__ import annotations

import hashlib
import io

from fastapi import APIRouter, HTTPException
from PIL import Image

import logic
from config import API_PUBLIC_URL, IMAGE_DIR, logger
from schemas import ImageStoreRequest, SceneGenerateRequest, SceneValidateRequest
from services.image import decode_data_url
from services.utils import scrub_payload

router = APIRouter(tags=["scene"])


@router.post("/scene/generate")
async def generate_scene_image(request: SceneGenerateRequest):
    logger.info("📥 [Scene Gen Req] %s", request.model_dump())
    return await logic.logic_generate_scene_image(request)


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
    return {"url": f"{API_PUBLIC_URL}/outputs/images/stored/{filename}"}


@router.post("/scene/validate_image")
async def validate_scene_image(request: SceneValidateRequest):
    logger.info("📥 [Scene Validate Req] %s", scrub_payload(request.model_dump()))
    return logic.logic_validate_scene_image(request)
