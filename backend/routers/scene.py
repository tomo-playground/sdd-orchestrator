"""Scene generation and validation endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import logger
from database import get_db, get_db_session
from models.scene import Scene
from schemas import (
    BatchSceneRequest,
    BatchSceneResponse,
    GeminiEditRequest,
    GeminiEditResponse,
    GeminiSuggestRequest,
    GeminiSuggestResponse,
    ImageGenAccepted,
    ImageProgressEvent,
    ImageStoreRequest,
    ImageStoreResponse,
    SceneCancelResponse,  # noqa: F401
    SceneEditImageRequest,
    SceneEditImageResponse,
    SceneGenerateRequest,
    SceneGenerateResponse,
    SceneValidateRequest,
    SceneValidationResponse,
    ValidateAndAutoEditResponse,  # noqa: F401
)
from services.asset_service import AssetService
from services.error_responses import raise_user_error
from services.generation import generate_scene_image
from services.image import decode_data_url, load_as_data_url
from services.image_gen_pipeline import run_image_gen
from services.image_progress import (
    ImageGenStage,
    create_image_task,
    get_image_task,
)
from services.imagen_edit import get_imagen_service
from services.utils import scrub_payload
from services.validation import validate_scene_image

router = APIRouter(tags=["scene"])

# Background task tracking to prevent GC of fire-and-forget tasks
_background_tasks: set[asyncio.Task] = set()


def _track_task(task: asyncio.Task) -> None:
    """Register a background task and auto-remove on completion."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.post("/scene/generate", response_model=SceneGenerateResponse)
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


@router.post("/scene/generate-batch", response_model=BatchSceneResponse)
async def generate_batch_images(request: BatchSceneRequest):
    """Generate images for multiple scenes concurrently with semaphore-based throttling."""

    from config import SD_BATCH_CONCURRENCY

    semaphore = asyncio.Semaphore(SD_BATCH_CONCURRENCY)

    async def _generate_one(scene_req: SceneGenerateRequest, index: int):
        async with semaphore:
            try:
                result = await generate_scene_image(scene_req)
                return {"index": index, "status": "success", "data": SceneGenerateResponse(**result)}
            except Exception as e:
                logger.exception("[Batch Gen] Scene %d failed: %s", index, e)
                return {"index": index, "status": "failed", "error": "Image generation failed"}

    tasks = [_generate_one(req, i) for i, req in enumerate(request.scenes)]
    results = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    return {
        "results": sorted(results, key=lambda r: r["index"]),
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
    }


@router.post("/image/store", response_model=ImageStoreResponse)
def store_scene_image(request: ImageStoreRequest, db: Session = Depends(get_db)):
    try:
        image_bytes = decode_data_url(request.image_b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc

    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    file_name = request.file_name or f"scene_{digest}.png"

    asset_service = AssetService(db)
    try:
        asset = asset_service.save_scene_image(
            image_bytes=image_bytes,
            project_id=request.project_id,
            group_id=request.group_id,
            storyboard_id=request.storyboard_id,
            scene_id=request.scene_id,
            file_name=file_name,
        )

        # Update Scene record (scene may have been recreated with a new ID)
        if request.scene_id:
            from services.storyboard.helpers import resolve_scene_id_by_client_id

            resolved_id = resolve_scene_id_by_client_id(db, request.scene_id, request.client_id, request.storyboard_id)
            if resolved_id:
                db_scene = db.query(Scene).filter(Scene.id == resolved_id, Scene.deleted_at.is_(None)).first()
                if db_scene:
                    db_scene.image_asset_id = asset.id
                    db.add(db_scene)
                    db.commit()

        url = asset_service.get_asset_url(asset.storage_key)
        logger.info("💾 [Image Store] Saved: %s", asset.storage_key)
        return {"url": url, "asset_id": asset.id}
    except Exception as e:
        raise_user_error("image_store", e)


@router.post("/scene/validate_image", response_model=SceneValidationResponse)
async def validate_scene_image_endpoint(request: SceneValidateRequest, db: Session = Depends(get_db)):
    logger.info("📥 [Scene Validate Req] %s", scrub_payload(request.model_dump()))
    return validate_scene_image(request, db=db)


@router.post("/scene/validate-and-auto-edit", response_model=ValidateAndAutoEditResponse)
async def validate_and_auto_edit_scene(request: SceneValidateRequest, db: Session = Depends(get_db)):
    """WD14 검증 + Gemini 자동 편집 (조건부)

    이미지 검증 후 Match Rate가 임계값 미만이면 자동으로 Gemini 편집을 실행합니다.

    Args:
        request: SceneValidateRequest
            - image_url: 검증할 이미지 URL
            - prompt: 원본 프롬프트
            - storyboard_id: 스토리보드 ID (비용 추적용)
            - scene_id: 씬 ID (재시도 카운트용)

    Returns:
        {
            "validation_result": {...},  # WD14 검증 결과
            "auto_edit_triggered": True/False,
            "edited_image": "base64" (if edited),
            "edit_cost": 0.0404 (if edited),
            "original_match_rate": 0.65,
            "final_match_rate": 0.88 (if edited)
        }

    비용 제어:
        - GEMINI_AUTO_EDIT_ENABLED=false → 자동 편집 안 함
        - match_rate >= threshold → 자동 편집 안 함
        - 스토리보드 비용 한도 초과 → 자동 편집 안 함
        - 씬 재시도 횟수 초과 → 자동 편집 안 함
    """
    from sqlalchemy import func

    from config import runtime_settings
    from models import ActivityLog

    rs = runtime_settings

    # Step 1: WD14 검증
    logger.info("📥 [Validate + Auto-Edit] %s", scrub_payload(request.model_dump()))
    validation_result = validate_scene_image(request, db=db)
    match_rate = validation_result.get("adjusted_match_rate", validation_result.get("match_rate", 1.0))
    missing_tags = validation_result.get("missing_tags", [])

    result = {
        "validation_result": validation_result,
        "auto_edit_triggered": False,
    }

    # Step 2: 자동 편집 체크 (Multi-Level Safety)

    # Check 1: 글로벌 스위치
    if not rs.auto_edit_enabled:
        logger.debug("[Auto Edit] Skipped (globally disabled)")
        return result

    # Check 2: 임계값 체크
    if match_rate >= rs.auto_edit_threshold:
        logger.debug("[Auto Edit] Skipped (match_rate=%.2f >= %.2f)", match_rate, rs.auto_edit_threshold)
        return result

    # Check 3: 스토리보드 비용 한도 체크
    if request.storyboard_id:
        current_cost = (
            db.query(func.sum(ActivityLog.gemini_cost_usd))
            .filter(ActivityLog.storyboard_id == request.storyboard_id)
            .scalar()
            or 0.0
        )

        if current_cost >= rs.auto_edit_max_cost:
            logger.warning(
                "[Auto Edit] Skipped (cost limit reached: $%.2f >= $%.2f)",
                current_cost,
                rs.auto_edit_max_cost,
            )
            result["skip_reason"] = "cost_limit_reached"
            result["current_cost"] = current_cost
            return result

        # Check 4: 씬 재시도 횟수 체크
        if request.scene_id:
            retry_count = (
                db.query(func.count(ActivityLog.id))
                .filter(
                    ActivityLog.storyboard_id == request.storyboard_id,
                    ActivityLog.scene_id == request.scene_id,
                    ActivityLog.gemini_edited == True,  # noqa: E712
                )
                .scalar()
            )

            if retry_count >= rs.auto_edit_max_retries:
                logger.warning("[Auto Edit] Skipped (max retries reached: %d)", retry_count)
                result["skip_reason"] = "max_retries_reached"
                result["retry_count"] = retry_count
                return result

    # === 모든 체크 통과 → 자동 편집 실행 ===
    logger.info("[Auto Edit] Triggered (match_rate=%.2f < %.2f)", match_rate, rs.auto_edit_threshold)

    # Release DB connection before Gemini API call (10-30s)
    db.close()

    try:
        from services.imagen_edit import auto_edit_with_gemini

        # Load image as base64 (from image_url or image_b64)
        source = request.image_b64 or request.image_url
        image_b64 = load_as_data_url(source)

        # Execute auto-edit
        edit_result = await auto_edit_with_gemini(
            image_b64=image_b64, original_prompt=request.prompt, match_rate=match_rate, missing_tags=missing_tags
        )

        result["auto_edit_triggered"] = True
        result["edited_image"] = edit_result["edited_image"]
        result["edit_cost"] = edit_result["cost_usd"]
        result["original_match_rate"] = match_rate
        result["edit_type"] = edit_result.get("edit_type", "unknown")

        logger.info(f"✅ [Auto Edit] Success (type={result['edit_type']}, cost=${result['edit_cost']:.4f})")

        # 편집된 이미지 WD14 재검증 (final_match_rate 기록용)
        try:
            revalidation = validate_scene_image(
                SceneValidateRequest(
                    image_b64=edit_result["edited_image"],
                    prompt=request.prompt,
                    storyboard_id=request.storyboard_id,
                    scene_id=request.scene_id,
                    character_id=request.character_id,
                ),
            )
            result["final_match_rate"] = revalidation.get("adjusted_match_rate", revalidation.get("match_rate"))
        except Exception:
            logger.warning("[Auto Edit] Revalidation failed, final_match_rate unavailable")

    except Exception as e:
        logger.exception("[Auto Edit] Failed: %s", e)
        result["auto_edit_error"] = "자동 편집에 실패했습니다."

    # Record Gemini edit in ActivityLog for cost/retry tracking
    if result.get("auto_edit_triggered"):
        try:
            with get_db_session() as edit_db:
                edit_log = ActivityLog(
                    storyboard_id=request.storyboard_id,
                    scene_id=request.scene_id,
                    prompt=request.prompt or "",
                    gemini_edited=True,
                    gemini_cost_usd=result.get("edit_cost"),
                    original_match_rate=match_rate,
                    final_match_rate=result.get("final_match_rate"),
                    status="success",
                )
                edit_db.add(edit_log)
                edit_db.commit()
                result["edit_log_id"] = edit_log.id
                logger.info(
                    f"📝 [Auto Edit] ActivityLog #{edit_log.id} recorded (cost=${result.get('edit_cost', 0):.4f})"
                )
        except Exception as log_err:
            logger.warning("[Auto Edit] ActivityLog insert failed (edit succeeded): %s", log_err)

    return result


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
            image_b64 = load_as_data_url(request.image_url)
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
        raise_user_error("image_edit", e)


@router.post("/scenes/{scene_id}/edit-image", response_model=SceneEditImageResponse)
async def edit_scene_image(scene_id: int, request: SceneEditImageRequest, db: Session = Depends(get_db)):
    """자연어 지시로 씬 이미지 편집

    기존 씬 이미지를 Gemini로 편집합니다. 캐릭터 edit-preview 패턴 재사용.
    """
    scene = db.query(Scene).filter(Scene.id == scene_id, Scene.deleted_at.is_(None)).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # 이미지 소스 결정: request → scene asset
    image_b64 = request.image_b64
    if not image_b64 and request.image_url:
        image_b64 = load_as_data_url(request.image_url)
    elif not image_b64 and scene.image_asset_id:
        asset_service = AssetService(db)
        from models.media_asset import MediaAsset

        asset = db.get(MediaAsset, scene.image_asset_id)
        if asset:
            image_b64 = load_as_data_url(asset_service.get_asset_url(asset.storage_key))

    if not image_b64:
        raise HTTPException(status_code=400, detail="No image source available")

    original_prompt = request.original_prompt or scene.image_prompt or ""

    # Extract values before closing DB to avoid DetachedInstanceError
    scene_storyboard_id = scene.storyboard_id

    # Release DB before Gemini API call
    db.close()

    try:
        imagen_service = get_imagen_service()
        result = await imagen_service.edit_with_analysis(
            image_b64=image_b64,
            original_prompt=original_prompt,
            target_change=request.edit_instruction,
        )

        edited_b64 = result["edited_image"]
        edit_type = result.get("edit_result", {}).get("edit_type", "pose")
        cost_usd = result["cost_usd"]

        # 편집된 이미지를 Asset으로 저장
        edited_bytes = decode_data_url(f"data:image/png;base64,{edited_b64}")
        asset_service = AssetService(db)

        from models.group import Group
        from models.storyboard import Storyboard

        sb = db.query(Storyboard).filter(Storyboard.id == scene_storyboard_id).first()
        group_id = sb.group_id if sb else 0
        grp = db.query(Group).filter(Group.id == group_id).first() if group_id else None
        project_id = grp.project_id if grp else 0

        # Re-fetch scene after db reconnect
        scene = db.query(Scene).filter(Scene.id == scene_id, Scene.deleted_at.is_(None)).first()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found after edit")

        asset = asset_service.save_scene_image(
            image_bytes=edited_bytes,
            project_id=project_id,
            group_id=group_id,
            storyboard_id=scene_storyboard_id,
            scene_id=scene_id,
            file_name=f"scene_{scene_id}_edited.png",
        )
        scene.image_asset_id = asset.id
        db.add(scene)
        db.commit()

        url = asset_service.get_asset_url(asset.storage_key)

        return SceneEditImageResponse(
            ok=True,
            edited_image=edited_b64,
            image_url=url,
            asset_id=asset.id,
            cost_usd=cost_usd,
            edit_type=edit_type,
        )
    except Exception as e:
        raise_user_error("scene_edit_image", e)


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
            image_b64 = load_as_data_url(request.image_url)
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
        raise_user_error("image_suggest", e)


# ------------------------------------------------------------------
# Async image generation + SSE progress stream
# ------------------------------------------------------------------


@router.post("/scene/generate-async", response_model=ImageGenAccepted, status_code=202)
async def generate_scene_async(request: SceneGenerateRequest):
    """Start async image generation and return task_id for SSE polling."""
    logger.info("[Scene Gen Async] %s", scrub_payload(request.model_dump()))
    task = create_image_task()
    _track_task(asyncio.create_task(run_image_gen(task.task_id, request)))
    return ImageGenAccepted(task_id=task.task_id)


@router.post("/scene/cancel/{task_id}", response_model=SceneCancelResponse)
async def cancel_image_gen(task_id: str):
    """Cancel an in-progress image generation task."""
    task = get_image_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.stage in (ImageGenStage.COMPLETED, ImageGenStage.FAILED):
        return SceneCancelResponse(ok=False, reason="Task already finished")
    task.cancelled = True
    task.stage = ImageGenStage.FAILED
    task.error = "Cancelled by user"
    task.notify()
    logger.info("[Scene Gen] Task %s cancelled", task_id)
    return SceneCancelResponse(ok=True)


@router.get(
    "/scene/progress/{task_id}",
    responses={
        200: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "SSE stream of ImageProgressEvent JSON objects",
        },
        404: {"description": "Task not found"},
    },
)
async def stream_image_progress(task_id: str):
    """Stream image generation progress via Server-Sent Events (SSE).

    Returns a stream of `data: {ImageProgressEvent}` messages until
    the task reaches COMPLETED or FAILED stage.
    """
    task = get_image_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return StreamingResponse(
        _image_event_generator(task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _image_event_generator(task_id: str) -> AsyncGenerator[str]:
    """Yield SSE events until the image task completes or fails."""
    try:
        while True:
            task = get_image_task(task_id)
            if not task:
                event = ImageProgressEvent(task_id=task_id, stage="failed", error="Task expired")
                yield f"data: {json.dumps(event.model_dump())}\n\n"
                return

            event = ImageProgressEvent(
                task_id=task.task_id,
                stage=task.stage.value,
                percent=task.percent,
                message=task.message,
                preview_image=task.preview_image,
                image=task.result.get("image") if task.result else None,
                used_prompt=task.result.get("used_prompt") if task.result else None,
                warnings=task.result.get("warnings", []) if task.result else [],
                error=task.error,
                controlnet_pose=task.result.get("controlnet_pose") if task.result else None,
                ip_adapter_reference=task.result.get("ip_adapter_reference") if task.result else None,
                image_url=task.result.get("image_url") if task.result else None,
                image_asset_id=task.result.get("image_asset_id") if task.result else None,
            )
            yield f"data: {json.dumps(event.model_dump())}\n\n"

            if task.stage in (ImageGenStage.COMPLETED, ImageGenStage.FAILED):
                await asyncio.sleep(2)
                return

            version = task._version
            updated = await task.wait_for_update(version, timeout=10.0)
            if not updated:
                yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        logger.debug("[SSE] Client disconnected for image task %s", task_id)
    except Exception:
        logger.exception("[SSE] Error in image progress stream for task %s", task_id)
        error_event = ImageProgressEvent(task_id=task_id, stage="failed", error="Internal error")
        yield f"data: {json.dumps(error_event.model_dump())}\n\n"
