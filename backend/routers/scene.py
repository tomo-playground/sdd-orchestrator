"""Scene generation and validation endpoints."""

from __future__ import annotations

import hashlib
import io

from fastapi import APIRouter, HTTPException
from PIL import Image

from config import API_PUBLIC_URL, IMAGE_DIR, logger
from schemas import (
    GeminiEditRequest,
    GeminiEditResponse,
    GeminiSuggestRequest,
    GeminiSuggestResponse,
    ImageStoreRequest,
    SceneGenerateRequest,
    SceneValidateRequest,
)
from services.generation import generate_scene_image
from services.image import decode_data_url, load_image_bytes
from services.imagen_edit import get_imagen_service
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
    return {"url": f"/outputs/images/stored/{filename}"}


@router.post("/scene/validate_image")
async def validate_scene_image_endpoint(request: SceneValidateRequest):
    logger.info("📥 [Scene Validate Req] %s", scrub_payload(request.model_dump()))
    return validate_scene_image(request)


@router.post("/scene/edit-with-gemini", response_model=GeminiEditResponse)
async def edit_scene_with_gemini(request: GeminiEditRequest):
    """Gemini Nano Banana로 씬 이미지 편집

    Match Rate가 낮거나 특정 요소(포즈/표정/시선)를 수정하고 싶을 때 사용합니다.

    Args:
        request: GeminiEditRequest
            - image_b64: Base64 인코딩된 원본 이미지
            - original_prompt: 원본 프롬프트
            - target_change: 목표 변경사항 (예: "sitting on chair with hands on lap")
            - edit_type: 편집 타입 (None이면 자동 감지)

    Returns:
        GeminiEditResponse
            - edited_image: Base64 인코딩된 편집된 이미지
            - cost_usd: 비용
            - edit_type: 적용된 편집 타입
            - analysis: Vision 분석 결과 (선택)

    비용: ~$0.0404/edit (Vision $0.0003 + Edit $0.0401)

    예시:
        POST /scene/edit-with-gemini
        {
            "image_b64": "data:image/png;base64,...",
            "original_prompt": "1girl, standing, indoors",
            "target_change": "sitting on chair with hands on lap",
            "edit_type": null  // 자동 감지
        }
    """
    try:
        logger.info("📥 [Gemini Edit Req] target_change: %s", request.target_change)

        # Get image as base64
        if request.image_b64:
            image_b64 = request.image_b64
        elif request.image_url:
            # Load image from URL and convert to base64
            image_bytes = load_image_bytes(request.image_url)
            import base64
            image_b64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        else:
            raise HTTPException(status_code=400, detail="Either image_url or image_b64 must be provided")

        # Gemini 서비스 가져오기
        imagen_service = get_imagen_service()

        # 자동 분석 후 편집
        result = await imagen_service.edit_with_analysis(
            image_b64=image_b64,
            original_prompt=request.original_prompt,
            target_change=request.target_change,
        )

        # Ensure edit_type is valid before creating response
        valid_types = ["pose", "expression", "gaze", "framing", "hands"]
        edit_type = result["edit_result"]["edit_type"]
        if edit_type not in valid_types:
            logger.warning(f"⚠️ Invalid edit_type '{edit_type}', defaulting to 'pose'")
            edit_type = "pose"

        logger.info(
            "✅ [Gemini Edit] Success (type: %s, cost: $%.4f)",
            edit_type,
            result["cost_usd"],
        )

        return GeminiEditResponse(
            edited_image=result["edited_image"],
            cost_usd=result["cost_usd"],
            edit_type=edit_type,
            analysis=result["analysis"],
        )

    except Exception as e:
        logger.error("❌ [Gemini Edit] Failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e



@router.post("/scene/suggest-edit", response_model=GeminiSuggestResponse)
async def suggest_edit_for_scene(request: GeminiSuggestRequest):
    """Gemini로 이미지와 프롬프트를 비교해 자동 제안 생성

    한국어 프롬프트와 실제 이미지를 비교하여 불일치를 발견하고,
    사용자가 수동으로 승인할 수 있는 편집 제안을 생성합니다.

    Args:
        request: GeminiSuggestRequest
            - image_url: 이미지 URL (Backend에서 fetch)
            - image_b64: Base64 인코딩된 이미지 (대체)
            - original_prompt: 한국어 프롬프트

    Returns:
        GeminiSuggestResponse
            - has_mismatch: 불일치 발견 여부
            - suggestions: 편집 제안 목록
            - cost_usd: 비용 (Vision API: ~$0.0003)

    예시:
        POST /scene/suggest-edit
        {
            "image_url": "http://localhost:8000/outputs/images/scene_abc123.png",
            "original_prompt": "1girl, sitting, indoors, smiling"
        }

        Response:
        {
            "has_mismatch": true,
            "suggestions": [
                {
                    "issue": "포즈 불일치",
                    "description": "프롬프트에는 'sitting'이 있지만 이미지는 서 있습니다",
                    "target_change": "의자에 앉은 포즈로 변경",
                    "confidence": 0.85,
                    "edit_type": "pose"
                }
            ],
            "cost_usd": 0.0003
        }
    """
    try:
        logger.info("📥 [Gemini Suggest] prompt: %s", request.original_prompt[:50])

        # Get image as base64
        if request.image_b64:
            image_b64 = request.image_b64
        elif request.image_url:
            # Load image from URL and convert to base64
            image_bytes = load_image_bytes(request.image_url)
            import base64
            image_b64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        else:
            raise HTTPException(status_code=400, detail="Either image_url or image_b64 must be provided")

        # Gemini 서비스 가져오기
        imagen_service = get_imagen_service()

        # 자동 제안 생성
        result = await imagen_service.suggest_edit_from_prompt(
            image_b64=image_b64,
            original_prompt_ko=request.original_prompt,
        )

        logger.info(
            "✅ [Gemini Suggest] %d suggestions generated (cost: $%.4f)",
            len(result.get("suggestions", [])),
            result["cost_usd"],
        )

        return GeminiSuggestResponse(
            has_mismatch=result["has_mismatch"],
            suggestions=result.get("suggestions", []),
            cost_usd=result["cost_usd"],
        )

    except Exception as e:
        logger.error("❌ [Gemini Suggest] Failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
