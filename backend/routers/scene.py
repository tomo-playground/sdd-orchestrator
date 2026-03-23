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
    BatchValidateRequest,
    BatchValidateResponse,
    ImageGenAccepted,
    ImageProgressEvent,
    ImageStoreRequest,
    ImageStoreResponse,
    SceneCancelResponse,  # noqa: F401
    SceneGenerateRequest,
    SceneGenerateResponse,
    SceneValidateRequest,
    SceneValidationResponse,
    TtsPrebuildRequest,
    TtsPrebuildResponse,
)
from services.asset_service import AssetService
from services.error_responses import raise_user_error
from services.generation import generate_scene_image
from services.image import decode_data_url
from services.image_gen_pipeline import run_image_gen
from services.image_progress import (
    ImageGenStage,
    create_image_task,
    get_image_task,
)
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
    if request.width != 832 or request.height != 1216:
        logger.debug(
            "Non-standard resolution: %dx%d (recommended: 832x1216)",
            request.width,
            request.height,
        )

    logger.info("📥 [Scene Gen Req] %s", request.model_dump())
    return await generate_scene_image(request)


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


@router.post("/scene/validate-image", response_model=SceneValidationResponse)
async def validate_scene_image_endpoint(request: SceneValidateRequest, db: Session = Depends(get_db)):
    logger.info("📥 [Scene Validate Req] %s", scrub_payload(request.model_dump()))
    result = validate_scene_image(request, db=db)

    # Phase 33: Fire-and-forget Gemini evaluation for non-WD14 tags
    gemini_tokens = result.get("gemini_tokens", [])
    if gemini_tokens and result.get("image_b64"):
        from services.validation import apply_gemini_evaluation

        task = asyncio.create_task(
            apply_gemini_evaluation(
                storyboard_id=request.storyboard_id,
                scene_id=request.scene_id or request.scene_index,
                image_b64=result["image_b64"],
                gemini_tokens=gemini_tokens,
                wd14_matched=result.get("wd14_matched", 0),
                wd14_total=result.get("wd14_total", 0),
                db_factory=get_db_session,
            )
        )
        _track_task(task)

    return result


@router.post("/scene/validate-batch", response_model=BatchValidateResponse)
async def validate_batch_images(request: BatchValidateRequest, db: Session = Depends(get_db)):
    """Batch validate multiple scenes — Gemini 호출 병합 (Phase 33 E-2).

    WD14는 씬별 개별 실행, Gemini는 이미지 기준 병합하여 API 호출 최소화.
    """
    from services.validation import batch_apply_gemini_evaluation

    results = []
    gemini_items = []

    for i, scene_req in enumerate(request.scenes):
        try:
            result = validate_scene_image(scene_req, db=db)
            # Strip internal fields to save memory (N scenes × large base64)
            response_data = {k: v for k, v in result.items() if k not in ("image_b64", "wd14_matched", "wd14_total")}
            results.append({"index": i, "status": "success", "data": response_data})

            # Collect Gemini evaluation items
            gemini_tokens = result.get("gemini_tokens", [])
            if gemini_tokens and result.get("image_b64"):
                gemini_items.append(
                    {
                        "result_index": i,
                        "storyboard_id": scene_req.storyboard_id,
                        "scene_id": scene_req.scene_id or scene_req.scene_index,
                        "image_b64": result["image_b64"],
                        "gemini_tokens": gemini_tokens,
                        "wd14_matched": result.get("wd14_matched", 0),
                        "wd14_total": result.get("wd14_total", 0),
                    }
                )
        except Exception as e:
            logger.exception("[Batch Validate] Scene %d failed: %s", i, e)
            results.append({"index": i, "status": "failed", "error": str(e)})

    # Fire single batched Gemini background task
    gemini_pending = 0
    if gemini_items:
        gemini_pending = len(gemini_items)
        task = asyncio.create_task(
            batch_apply_gemini_evaluation(
                items=gemini_items,
                db_factory=get_db_session,
            )
        )
        _track_task(task)

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    return {
        "results": sorted(results, key=lambda r: r["index"]),
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "gemini_pending": gemini_pending,
    }


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


@router.post("/scene/tts-prebuild", response_model=TtsPrebuildResponse)
async def tts_prebuild(request: TtsPrebuildRequest, db: Session = Depends(get_db)):
    """Autopilot 렌더 전 TTS 사전 생성.

    - 이미 tts_asset_id가 있는 씬은 건너뛴다(skipped).
    - 나머지 씬을 TTS 생성 후 Scene.tts_asset_id를 업데이트한다(prebuilt).
    - 씬 단위 실패는 status='failed'로 기록하며 전체 요청은 200을 반환한다.
    """
    from services.tts_prebuild import prebuild_tts_for_scenes

    return await prebuild_tts_for_scenes(request, db)


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
                used_negative_prompt=task.result.get("used_negative_prompt") if task.result else None,
                used_steps=task.result.get("used_steps") if task.result else None,
                used_cfg_scale=task.result.get("used_cfg_scale") if task.result else None,
                used_sampler=task.result.get("used_sampler") if task.result else None,
                seed=task.result.get("seed") if task.result else None,
                warnings=task.result.get("warnings", []) if task.result else [],
                error=task.error,
                controlnet_pose=task.result.get("controlnet_pose") if task.result else None,
                ip_adapter_reference=task.result.get("ip_adapter_reference") if task.result else None,
                image_url=task.result.get("image_url") if task.result else None,
                image_asset_id=task.result.get("image_asset_id") if task.result else None,
                match_rate=task.result.get("match_rate") if task.result else None,
                matched_tags=task.result.get("matched_tags") if task.result else None,
                missing_tags=task.result.get("missing_tags") if task.result else None,
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
