"""Video creation and management endpoints."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import VIDEO_DIR, logger
from database import get_db
from schemas import VideoDeleteRequest, VideoRequest
from services.utils import scrub_payload
from services.video import create_video_task

router = APIRouter(prefix="/video", tags=["video"])


@router.post("/create")
async def create_video(request: VideoRequest, db: Session = Depends(get_db)):
    logger.info("📥 [Video Req] %s", scrub_payload(request.model_dump()))
    logger.info(f"🔍 [DEBUG] include_scene_text={request.include_scene_text}, scene_text_font={request.scene_text_font}")
    logger.info(f"🎤 [DEBUG] voice_preset_id={request.voice_preset_id}, voice_design_prompt={request.voice_design_prompt}, tts_engine={request.tts_engine}")
    res = await create_video_task(request)
    video_url = res.get("video_url")

    if video_url and request.storyboard_id:
        import json

        from models.storyboard import Storyboard

        storyboard = db.query(Storyboard).filter(Storyboard.id == request.storyboard_id).first()
        if storyboard:


            # Update recent_videos
            recent = []
            if storyboard.recent_videos_json:
                try:
                    recent = json.loads(storyboard.recent_videos_json)
                except Exception:
                    recent = []

            # Add new video to the beginning
            new_entry = {"url": video_url, "label": request.layout_style, "createdAt": int(time.time() * 1000)}
            recent = [new_entry] + recent[:9] # Keep last 10
            storyboard.recent_videos_json = json.dumps(recent)

            db.commit()
            logger.info("✅ Video associated with storyboard id=%d", request.storyboard_id)

    return res


@router.post("/delete")
async def delete_video(request: VideoDeleteRequest, db: Session = Depends(get_db)):
    """Delete video from storage, database, and storyboard references.

    Handles both legacy local files and S3-based media assets.
    """
    from models.media_asset import MediaAsset
    from models.storyboard import Storyboard
    from services.storage import get_storage

    filename = os.path.basename(request.filename or "")
    if not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage = get_storage()

    try:
        # Try to find MediaAsset by filename
        asset = db.query(MediaAsset).filter(
            MediaAsset.file_name == filename,
            MediaAsset.file_type == "video"
        ).first()

        if asset:
            logger.info(f"🗑️ Deleting video asset: {asset.storage_key} (ID: {asset.id})")

            # 1. Delete from S3 storage
            if storage.exists(asset.storage_key):
                storage.delete(asset.storage_key)
                logger.info(f"✅ Deleted from storage: {asset.storage_key}")

            # 2. Clear Storyboard references
            storyboards = db.query(Storyboard).filter(
                Storyboard.video_asset_id == asset.id
            ).all()
            for sb in storyboards:
                sb.video_asset_id = None
                logger.info(f"🔗 Cleared video_asset_id from Storyboard {sb.id}")

            # 3. Remove from recent_videos_json in all Storyboards
            import json
            all_storyboards = db.query(Storyboard).filter(
                Storyboard.recent_videos_json.isnot(None)
            ).all()

            for sb in all_storyboards:
                if not sb.recent_videos_json:  # Type guard
                    continue
                try:
                    recent = json.loads(sb.recent_videos_json)
                    if not isinstance(recent, list):
                        continue

                    # Filter out videos matching the deleted filename
                    original_count = len(recent)
                    recent = [v for v in recent if filename not in v.get("url", "")]

                    if len(recent) < original_count:
                        sb.recent_videos_json = json.dumps(recent) if recent else None
                        logger.info(f"🗑️ Removed from recent_videos in Storyboard {sb.id} ({original_count} → {len(recent)})")
                except Exception as e:
                    logger.warning(f"Failed to update recent_videos for Storyboard {sb.id}: {e}")

            # 3. Delete MediaAsset record
            db.delete(asset)
            db.commit()
            logger.info(f"✅ Deleted MediaAsset record ID: {asset.id}")

            return {"ok": True, "deleted": True, "asset_id": asset.id}

        # Fallback: Try legacy local file deletion
        target = VIDEO_DIR / filename
        if target.exists():
            logger.info(f"🗑️ Deleting legacy local file: {target}")
            target.unlink()
            logger.info(f"✅ Deleted local file: {filename}")
            return {"ok": True, "deleted": True, "legacy": True}

        logger.warning(f"⚠️ Video not found: {filename}")
        return {"ok": False, "deleted": False, "reason": "not_found"}

    except Exception as exc:
        logger.exception("Video delete failed")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/exists")
async def video_exists(filename: str = Query(..., min_length=1)):
    name = os.path.basename(filename)
    if not name.endswith(".mp4"):
        return {"exists": False}
    target = VIDEO_DIR / name
    return {"exists": target.exists()}


@router.get("/transitions")
async def get_transitions():
    """Get list of available scene transition effects."""
    from constants.transition import get_transition_list

    return {"transitions": get_transition_list()}


@router.post("/extract-caption")
async def extract_caption(request: dict):
    """Extract a concise caption from longer text using LLM.

    Accepts:
        - text: str (the long text to extract from)

    Returns:
        - caption: str (extracted concise caption, max 60 chars)
    """
    from config import GEMINI_TEXT_MODEL, gemini_client

    text = request.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    # If text is already short enough, return as-is
    if len(text) <= 60:
        return {"caption": text}

    try:
        prompt = f"""다음 텍스트에서 핵심 내용만 추출하여 60자 이내의 간결한 캡션을 만들어주세요.
규칙:
- 반드시 60자 이내로 작성
- 핵심 키워드와 주제만 포함
- 해시태그 포함 가능
- 이모지 사용 가능하지만 과도하지 않게

텍스트:
{text}

캡션만 출력하세요 (설명이나 따옴표 없이):"""

        response = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt
        )

        caption = response.text.strip()

        # Remove quotes if present
        if caption.startswith('"') and caption.endswith('"'):
            caption = caption[1:-1]
        if caption.startswith("'") and caption.endswith("'"):
            caption = caption[1:-1]

        # Ensure it's within 60 chars (hard truncate if needed)
        if len(caption) > 60:
            caption = caption[:60].rstrip()

        logger.info(f"📝 Caption extracted: {len(text)} chars → {len(caption)} chars")
        return {"caption": caption, "original_length": len(text)}

    except Exception:
        logger.exception("Caption extraction failed")
        # Fallback: simple truncation
        fallback = text[:60].rstrip()
        return {"caption": fallback, "fallback": True}


@router.post("/extract-hashtags")
async def extract_hashtags(request: dict):
    """Extract 3 hashtag keywords from topic text using LLM.

    Accepts:
        - text: str (topic text to extract keywords from)

    Returns:
        - caption: str (e.g. "#키워드1 #키워드2 #키워드3")
    """
    from config import GEMINI_TEXT_MODEL, gemini_client

    text = request.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    try:
        prompt = f"""다음 주제에서 핵심 키워드 3개를 해시태그로 추출하세요.

규칙:
- 정확히 3개의 해시태그
- 각 키워드는 한글 기준 5자 이내 (# 제외)
- 형식: #키워드1 #키워드2 #키워드3
- 해시태그만 출력 (설명이나 따옴표 없이)

주제:
{text}

해시태그:"""

        response = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )

        hashtags = response.text.strip()

        # Remove surrounding quotes
        for q in ('"', "'", "`"):
            if hashtags.startswith(q) and hashtags.endswith(q):
                hashtags = hashtags[1:-1]

        # Ensure within 60 chars
        if len(hashtags) > 60:
            hashtags = hashtags[:60].rstrip()

        logger.info(f"Hashtags extracted from topic: {hashtags}")
        return {"caption": hashtags, "original_topic": text}

    except Exception:
        logger.exception("Hashtag extraction failed")
        return {"caption": text[:57] + "...", "fallback": True}
