"""Async image generation pipeline: generate, validate, store.

Extracted from routers/scene.py to keep the router file focused on
endpoint definitions (W-1 file size guideline).
"""

from __future__ import annotations

import asyncio
import hashlib

from config import AUTO_REGEN_ENABLED, AUTO_REGEN_MAX_RETRIES, logger
from database import get_db_session
from models.scene import Scene
from schemas import SceneGenerateRequest
from services.asset_service import AssetService
from services.auto_regen import (
    describe_failure,
    has_critical_failure,
    shift_seed_for_retry,
    validate_for_critical_failure,
)
from services.generation import generate_scene_image
from services.image import decode_data_url
from services.image_progress import ImageGenStage, calc_percent, get_image_task
from services.sd_progress_poller import poll_sd_progress


def _sync_store_image(
    image_b64: str, storyboard_id: int, scene_id: int, client_id: str | None
) -> tuple[str | None, int | None]:
    """Synchronous MinIO storage + DB update (runs in a thread).

    Single transaction: asset creation + scene.image_asset_id update.
    Returns (url, asset_id) on success, (None, None) on failure.
    """
    from services.storyboard.helpers import resolve_project_group_ids, resolve_scene_id_by_client_id

    with get_db_session() as db:
        ids = resolve_project_group_ids(db, storyboard_id)
        if not ids:
            logger.warning("[Backend Store] storyboard %d not found", storyboard_id)
            return (None, None)
        project_id, group_id = ids

        resolved_id = resolve_scene_id_by_client_id(db, scene_id, client_id, storyboard_id)
        actual_scene_id = resolved_id or scene_id

        image_bytes = decode_data_url(f"data:image/png;base64,{image_b64}")
        digest = hashlib.sha256(image_bytes).hexdigest()[:16]
        file_name = f"scene_{actual_scene_id}_{digest}.png"

        asset_service = AssetService(db)
        asset = asset_service.save_scene_image(
            image_bytes=image_bytes,
            project_id=project_id,
            group_id=group_id,
            storyboard_id=storyboard_id,
            scene_id=actual_scene_id,
            file_name=file_name,
            auto_commit=False,
        )

        if resolved_id:
            db_scene = db.query(Scene).filter(Scene.id == resolved_id, Scene.deleted_at.is_(None)).first()
            if db_scene:
                db_scene.image_asset_id = asset.id
                db.add(db_scene)
            else:
                logger.warning("[Backend Store] scene %d not found after resolve", resolved_id)
        else:
            logger.warning("[Backend Store] scene not resolved (id=%d, client_id=%s)", scene_id, client_id)

        db.commit()
        url = asset_service.get_asset_url(asset.storage_key)
        logger.info("[Backend Store] Saved: %s (asset=%d)", asset.storage_key, asset.id)
        return (url, asset.id)


async def store_image_to_db(image_b64: str, request: SceneGenerateRequest) -> tuple[str | None, int | None]:
    """Backend-autonomous image storage (non-blocking).

    Returns (url, asset_id) on success, (None, None) on failure.
    """
    if not request.storyboard_id or not request.scene_id:
        return (None, None)

    return await asyncio.to_thread(
        _sync_store_image,
        image_b64,
        request.storyboard_id,
        request.scene_id,
        request.client_id,
    )


async def _run_wd14_validation(
    image_url: str,
    prompt: str,
    storyboard_id: int | None,
    scene_id: int | None,
    character_id: int | None,
) -> dict | None:
    """Run WD14 validation after image storage. Silent fail on any error.

    Runs in a thread to avoid blocking the async event loop (ONNX inference).
    Returns validation result dict or None on failure.
    """

    def _sync_validate() -> dict | None:
        try:
            from schemas import SceneValidateRequest
            from services.validation import validate_scene_image

            req = SceneValidateRequest(
                image_url=image_url,
                prompt=prompt,
                storyboard_id=storyboard_id,
                scene_id=scene_id,
                character_id=character_id,
            )
            with get_db_session() as db:
                return validate_scene_image(req, db=db)
        except Exception as exc:
            logger.warning("[WD14 Auto-Validate] Silent fail: %s", exc)
            return None

    try:
        return await asyncio.to_thread(_sync_validate)
    except Exception as exc:
        logger.warning("[WD14 Auto-Validate] Thread error: %s", exc)
        return None


async def generate_and_validate(task, request: SceneGenerateRequest) -> dict | None:
    """Single generation attempt: compose -> generate -> store -> validate.

    Returns result dict (with optional _critical_failure key), or None if cancelled.
    """
    task.stage = ImageGenStage.COMPOSING
    task.percent = calc_percent(task)
    task.message = "프롬프트 조합 중..."
    task.notify()

    if task.cancelled:
        return None

    task.stage = ImageGenStage.GENERATING
    task.percent = calc_percent(task)
    task.message = "이미지 생성 중..."
    task.notify()

    poller = asyncio.create_task(poll_sd_progress(task))
    try:
        result = await generate_scene_image(request)
    finally:
        poller.cancel()

    if task.cancelled:
        return None

    task.stage = ImageGenStage.STORING
    task.percent = calc_percent(task)
    task.message = "저장 중..."
    task.notify()

    task.stage = ImageGenStage.VALIDATING
    task.percent = calc_percent(task)
    task.message = "품질 검증 중..."
    task.notify()

    prompt = result.get("used_prompt") or request.prompt
    critical = validate_for_critical_failure(result, prompt)
    if critical:
        result["_critical_failure"] = critical

    return result


async def run_image_gen(task_id: str, request: SceneGenerateRequest) -> None:
    """Background coroutine: generate image with auto-retry on critical failure."""
    task = get_image_task(task_id)
    if not task:
        return

    try:
        result = await generate_and_validate(task, request)
        if result is None:
            return

        retries = 0
        while AUTO_REGEN_ENABLED and retries < AUTO_REGEN_MAX_RETRIES and has_critical_failure(result):
            retries += 1
            reason = describe_failure(result)
            logger.warning("[Auto-Regen] %s detected, retry %d/%d", reason, retries, AUTO_REGEN_MAX_RETRIES)

            task.stage = ImageGenStage.RETRYING
            task.percent = calc_percent(task)
            task.message = f"재생성 중 ({retries}/{AUTO_REGEN_MAX_RETRIES}): {reason}"
            task.notify()

            # Clear ComfyUI cache before retry (blank image often caused by stale cache)
            try:
                from services.sd_client.factory import get_sd_client

                await get_sd_client().clear_cache()
            except Exception:
                pass
            shift_seed_for_retry(request, retries)
            result = await generate_and_validate(task, request)
            if result is None:
                return

        # Backend-autonomous store: save to MinIO + update scene
        if result and result.get("image") and request.storyboard_id:
            try:
                url, asset_id = await store_image_to_db(result["image"], request)
                if url:
                    result["image_url"] = url
                    result["image_asset_id"] = asset_id

                    # WD14 validation after storage (silent fail)
                    validation = await _run_wd14_validation(
                        image_url=url,
                        prompt=result.get("used_prompt") or request.prompt,
                        storyboard_id=request.storyboard_id,
                        scene_id=request.scene_id,
                        character_id=request.character_id,
                    )
                    if validation:
                        result["match_rate"] = validation.get("match_rate")
                        result["matched_tags"] = validation.get("matched")
                        result["missing_tags"] = validation.get("missing")
            except Exception as exc:
                logger.warning("[Backend Store] failed, client fallback: %s", exc)

        # Stage: completed
        task.stage = ImageGenStage.COMPLETED
        task.percent = 100
        task.result = result
        task.message = "완료" if retries == 0 else f"완료 (재시도 {retries}회)"
        task.notify()

    except Exception as exc:
        logger.exception("[Scene Gen Async] Failed for task %s", task_id)
        task.stage = ImageGenStage.FAILED
        task.error = str(exc)
        task.notify()
