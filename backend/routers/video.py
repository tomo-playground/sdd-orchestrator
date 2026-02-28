"""Video creation and management endpoints."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import VIDEO_DIR, logger
from database import SessionLocal, get_db
from models.media_asset import MediaAsset
from models.render_history import RenderHistory
from schemas import (  # noqa: F401
    CaptionExtractResponse,
    HashtagExtractResponse,
    PaginatedRenderHistoryList,
    RenderHistoryItem,
    RenderHistoryLookupResponse,
    RenderProgressEvent,
    TextExtractRequest,
    TransitionsResponse,
    VideoCreateAccepted,
    VideoCreateResponse,
    VideoDeleteRequest,
    VideoDeleteResponse,
    VideoExistsResponse,
    VideoRequest,
    YouTubeStatusesRequest,
    YouTubeStatusesResponse,
)
from services.utils import scrub_payload
from services.video import create_video_task
from services.video.builder import VideoBuilder
from services.video.progress import RenderStage, create_task, estimate_remaining, get_task

router = APIRouter(prefix="/video", tags=["video"])

# Background task tracking to prevent GC of fire-and-forget tasks
_background_tasks: set[asyncio.Task] = set()


def _track_task(task: asyncio.Task) -> None:
    """Register a background task and auto-remove on completion."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# ------------------------------------------------------------------
# Helper: Save render history (shared by sync and async endpoints)
# ------------------------------------------------------------------


def _save_render_history(db: Session, request: VideoRequest, result: dict) -> int | None:
    """Save RenderHistory row and return its id, or None."""
    video_url = result.get("video_url")
    media_asset_id = result.get("media_asset_id")
    if video_url and request.storyboard_id and media_asset_id:
        rh = RenderHistory(
            storyboard_id=request.storyboard_id,
            media_asset_id=media_asset_id,
            label=request.layout_style or "full",
        )
        db.add(rh)
        db.commit()
        db.refresh(rh)
        logger.info("RenderHistory created id=%d for storyboard id=%d", rh.id, request.storyboard_id)
        return rh.id
    if video_url:
        missing = []
        if not request.storyboard_id:
            missing.append("storyboard_id")
        if not media_asset_id:
            missing.append("media_asset_id")
        logger.warning("Video created but RenderHistory skipped (missing: %s)", ", ".join(missing))
    return None


# ------------------------------------------------------------------
# Sync endpoint (backward compatible)
# ------------------------------------------------------------------


@router.post("/create", response_model=VideoCreateResponse)
async def create_video(request: VideoRequest):
    logger.info("[Video Req] %s", scrub_payload(request.model_dump()))
    res = await create_video_task(request)
    # Use a fresh session for render history (build may take 30-120s)
    db = SessionLocal()
    try:
        rh_id = _save_render_history(db, request, res)
        if rh_id is not None:
            res["render_history_id"] = rh_id
    finally:
        db.close()
    return res


# ------------------------------------------------------------------
# Async endpoint + SSE progress stream
# ------------------------------------------------------------------


@router.post("/create-async", response_model=VideoCreateAccepted, status_code=202)
async def create_video_async(request: VideoRequest):
    logger.info("[Video Async Req] %s", scrub_payload(request.model_dump()))
    task = create_task(total_scenes=len(request.scenes))
    _track_task(asyncio.create_task(_run_video_build(task.task_id, request)))
    return VideoCreateAccepted(task_id=task.task_id)


async def _run_video_build(task_id: str, request: VideoRequest) -> None:
    """Background coroutine: build video and save render history."""
    task = get_task(task_id)
    if not task:
        return
    try:
        builder = VideoBuilder(request)
        builder.set_progress(task)
        result = await builder.build()

        # Save render history BEFORE sending COMPLETED
        db = SessionLocal()
        try:
            rh_id = _save_render_history(db, request, result)
            if rh_id is not None:
                result["render_history_id"] = rh_id
        finally:
            db.close()

        # NOW send COMPLETED with full result (including render_history_id)
        task.transition_stage(RenderStage.COMPLETED)
        task.result = result
        task.percent = 100
        task.notify()
    except Exception as exc:
        logger.exception("[Video Async] Build failed for task %s", task_id)
        if task.stage != RenderStage.FAILED:
            task.transition_stage(RenderStage.FAILED)
            task.error = str(exc)
            task.notify()


@router.get(
    "/progress/{task_id}",
    responses={
        200: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "SSE stream of RenderProgressEvent JSON objects",
        },
        404: {"description": "Task not found"},
    },
)
async def stream_progress(task_id: str):
    """Stream video render progress via Server-Sent Events (SSE).

    Returns a stream of `data: {RenderProgressEvent}` messages until
    the task reaches COMPLETED or FAILED stage.
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return StreamingResponse(
        _event_generator(task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _event_generator(task_id: str) -> AsyncGenerator[str]:
    """Yield SSE events until the task completes or fails."""
    try:
        while True:
            task = get_task(task_id)
            if not task:
                yield _sse_event(RenderProgressEvent(task_id=task_id, stage="failed", error="Task expired"))
                return

            pct = task.percent
            elapsed = time.time() - task.created_at
            eta = estimate_remaining(task)

            event = RenderProgressEvent(
                task_id=task.task_id,
                stage=task.stage.value,
                percent=pct,
                message=task.message,
                encode_percent=task.encode_percent,
                current_scene=task.current_scene,
                total_scenes=task.total_scenes,
                elapsed_seconds=round(elapsed, 1),
                estimated_remaining_seconds=round(eta, 1) if eta is not None else None,
                video_url=task.result.get("video_url") if task.result else None,
                media_asset_id=task.result.get("media_asset_id") if task.result else None,
                render_history_id=task.result.get("render_history_id") if task.result else None,
                error=task.error,
            )
            yield _sse_event(event)

            if task.stage in (RenderStage.COMPLETED, RenderStage.FAILED):
                # Let client close EventSource first to avoid
                # ERR_INCOMPLETE_CHUNKED_ENCODING race condition
                await asyncio.sleep(2)
                return

            # Wait for next progress update (with timeout to send keep-alive)
            version = task._version
            updated = await task.wait_for_update(version, timeout=15.0)
            if not updated:
                yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        logger.debug("[SSE] Client disconnected for task %s", task_id)
    except Exception:
        logger.exception("[SSE] Error in video progress stream for task %s", task_id)
        error_event = RenderProgressEvent(task_id=task_id, stage="failed", error="Internal error")
        yield _sse_event(error_event)


def _sse_event(event: RenderProgressEvent) -> str:
    return f"data: {json.dumps(event.model_dump())}\n\n"


# ------------------------------------------------------------------
# Existing endpoints
# ------------------------------------------------------------------


@router.post("/delete", response_model=VideoDeleteResponse)
async def delete_video(request: VideoDeleteRequest, db: Session = Depends(get_db)):
    """Delete video from storage, database, and render_history references.

    Supports deletion by asset_id (preferred) or filename (legacy fallback).
    """
    from services.storage import get_storage

    if not request.asset_id and not request.filename:
        raise HTTPException(status_code=400, detail="Either asset_id or filename is required")

    # Validate filename before entering try block
    if request.filename and not os.path.basename(request.filename).endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage = get_storage()

    try:
        # Prefer asset_id lookup over filename
        asset = None
        if request.asset_id:
            asset = (
                db.query(MediaAsset).filter(MediaAsset.id == request.asset_id, MediaAsset.file_type == "video").first()
            )
        if not asset and request.filename:
            filename = os.path.basename(request.filename)
            asset = (
                db.query(MediaAsset).filter(MediaAsset.file_name == filename, MediaAsset.file_type == "video").first()
            )

        if asset:
            logger.info(f"Deleting video asset: {asset.storage_key} (ID: {asset.id})")

            # 1. Delete from S3 storage
            if storage.exists(asset.storage_key):
                storage.delete(asset.storage_key)
                logger.info(f"Deleted from storage: {asset.storage_key}")

            # 2. Remove render_history rows referencing this asset (CASCADE handles this too)
            deleted_count = (
                db.query(RenderHistory)
                .filter(RenderHistory.media_asset_id == asset.id)
                .delete(synchronize_session=False)
            )
            logger.info(f"Deleted {deleted_count} render_history rows by asset_id")

            # 3. Delete MediaAsset record
            db.delete(asset)
            db.commit()
            logger.info(f"Deleted MediaAsset record ID: {asset.id}")

            return {"ok": True, "deleted": True, "asset_id": asset.id}

        # Fallback: Try legacy local file deletion
        if request.filename:
            legacy_name = os.path.basename(request.filename)
            target = VIDEO_DIR / legacy_name
            if target.exists():
                logger.info("Deleting legacy local file: %s", target)
                target.unlink()
                return {"ok": True, "deleted": True, "legacy": True}

        identifier = request.asset_id or request.filename
        logger.warning("Video not found: %s", identifier)
        return {"ok": False, "deleted": False, "reason": "not_found"}

    except Exception as exc:
        db.rollback()
        from services.error_responses import raise_user_error

        raise_user_error("video_delete", exc)


@router.get("/exists", response_model=VideoExistsResponse)
async def video_exists(filename: str = Query(..., min_length=1)):
    name = os.path.basename(filename)
    if not name.endswith(".mp4"):
        return {"exists": False}
    target = VIDEO_DIR / name
    return {"exists": target.exists()}


@router.post("/youtube-statuses", response_model=YouTubeStatusesResponse)
async def batch_youtube_statuses(body: YouTubeStatusesRequest, db: Session = Depends(get_db)):
    """Get YouTube upload statuses for multiple video URLs."""
    statuses: dict[str, dict] = {}

    for url in body.video_urls[:10]:
        filename = os.path.basename(url.split("?")[0])
        asset = db.query(MediaAsset).filter(MediaAsset.file_name == filename, MediaAsset.file_type == "video").first()
        if not asset:
            continue
        rh = (
            db.query(RenderHistory)
            .filter(RenderHistory.media_asset_id == asset.id)
            .order_by(RenderHistory.id.desc())
            .first()
        )
        if rh and rh.youtube_video_id:
            statuses[url] = {
                "video_id": rh.youtube_video_id,
                "status": rh.youtube_upload_status,
            }

    return {"statuses": statuses}


@router.get("/render-history", response_model=PaginatedRenderHistoryList)
async def list_render_history(
    project_id: int | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """List render history for the gallery (newest first, latest per title+label)."""
    from sqlalchemy import func

    from models.group import Group
    from models.project import Project
    from models.storyboard import Storyboard

    # Subquery: 제목+라벨 조합별 최신 id만 선택 (같은 제목의 다른 스토리보드도 중복 제거)
    latest_sub = (
        db.query(func.max(RenderHistory.id).label("max_id"))
        .join(RenderHistory.storyboard)
        .filter(Storyboard.deleted_at.is_(None))
    )
    if project_id is not None:
        latest_sub = latest_sub.join(Storyboard.group).join(Group.project).filter(Project.id == project_id)
    latest_sub = latest_sub.group_by(Storyboard.title, RenderHistory.label).subquery()

    query = (
        db.query(RenderHistory)
        .join(latest_sub, RenderHistory.id == latest_sub.c.max_id)
        .join(RenderHistory.storyboard)
        .join(Storyboard.group)
        .join(Group.project)
        .join(RenderHistory.media_asset)
    )

    total = query.count()
    rows = query.order_by(RenderHistory.created_at.desc(), RenderHistory.id.desc()).offset(offset).limit(limit).all()

    items = []
    for rh in rows:
        sb = rh.storyboard
        grp = sb.group
        proj = grp.project
        items.append(
            RenderHistoryItem(
                id=rh.id,
                label=rh.label,
                url=rh.media_asset.url,
                created_at=rh.created_at,
                storyboard_id=sb.id,
                storyboard_title=sb.title,
                project_id=proj.id,
                project_name=proj.name,
                group_id=grp.id,
                group_name=grp.name,
            )
        )
    return PaginatedRenderHistoryList(items=items, total=total, offset=offset, limit=limit)


@router.get("/render-history-lookup", response_model=RenderHistoryLookupResponse)
async def lookup_render_history(video_url: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Look up render_history_id by video URL (filename match)."""
    filename = os.path.basename(video_url.split("?")[0])
    asset = db.query(MediaAsset).filter(MediaAsset.file_name == filename, MediaAsset.file_type == "video").first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")

    rh = (
        db.query(RenderHistory)
        .filter(RenderHistory.media_asset_id == asset.id)
        .order_by(RenderHistory.id.desc())
        .first()
    )
    if not rh:
        raise HTTPException(status_code=404, detail="Render history not found")

    return RenderHistoryLookupResponse(render_history_id=rh.id)


@router.get("/transitions", response_model=TransitionsResponse)
async def get_transitions():
    """Get list of available scene transition effects."""
    from constants.transition import get_transition_list

    return {"transitions": get_transition_list()}


@router.post("/extract-caption", response_model=CaptionExtractResponse)
async def extract_caption(request: TextExtractRequest):
    """Extract a concise caption from longer text using LLM."""
    from config import CAPTION_MAX_LENGTH, GEMINI_TEXT_MODEL, gemini_client

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    max_len = CAPTION_MAX_LENGTH
    if len(text) <= max_len:
        return CaptionExtractResponse(caption=text)

    try:
        prompt = (
            f"다음 텍스트에서 핵심 내용만 추출하여 {max_len}자 이내의 간결한 캡션을 만들어주세요.\n"
            f"규칙:\n- 반드시 {max_len}자 이내로 작성\n- 핵심 키워드와 주제만 포함\n"
            f"- 해시태그 포함 가능\n- 이모지 사용 가능하지만 과도하지 않게\n\n"
            f"텍스트:\n{text}\n\n캡션만 출력하세요 (설명이나 따옴표 없이):"
        )

        response = gemini_client.models.generate_content(model=GEMINI_TEXT_MODEL, contents=prompt)
        caption = _strip_quotes(response.text.strip() if response.text else text[:max_len])

        if len(caption) > max_len:
            caption = caption[:max_len].rstrip()

        logger.info("Caption extracted: %d chars -> %d chars", len(text), len(caption))
        return CaptionExtractResponse(caption=caption, original_length=len(text))

    except Exception:
        logger.exception("Caption extraction failed")
        return CaptionExtractResponse(caption=text[:max_len].rstrip(), fallback=True)


@router.post("/extract-hashtags", response_model=HashtagExtractResponse)
async def extract_hashtags(request: TextExtractRequest):
    """Extract 3 hashtag keywords from topic text using LLM."""
    from config import CAPTION_MAX_LENGTH, GEMINI_TEXT_MODEL, gemini_client

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    max_len = CAPTION_MAX_LENGTH
    try:
        prompt = (
            "다음 주제에서 핵심 키워드 3개를 해시태그로 추출하세요.\n\n"
            "규칙:\n- 정확히 3개의 해시태그\n- 각 키워드는 한글 기준 5자 이내 (# 제외)\n"
            "- 형식: #키워드1 #키워드2 #키워드3\n"
            f"- 해시태그만 출력 (설명이나 따옴표 없이)\n\n주제:\n{text}\n\n해시태그:"
        )

        response = gemini_client.models.generate_content(model=GEMINI_TEXT_MODEL, contents=prompt)
        hashtags = _strip_quotes(response.text.strip() if response.text else text[:max_len])

        if len(hashtags) > max_len:
            hashtags = hashtags[:max_len].rstrip()

        logger.info("Hashtags extracted from topic: %s", hashtags)
        return HashtagExtractResponse(caption=hashtags, original_topic=text)

    except Exception:
        logger.exception("Hashtag extraction failed")
        return HashtagExtractResponse(caption=text[: max_len - 3] + "...", fallback=True)


def _strip_quotes(text: str) -> str:
    """Remove surrounding quotes from LLM output."""
    for q in ('"', "'", "`"):
        if text.startswith(q) and text.endswith(q):
            text = text[1:-1]
    return text
