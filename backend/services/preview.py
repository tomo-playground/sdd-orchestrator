"""Preview service: TTS preview, frame preview, timeline, pre-validation.

Reuses existing helpers without VideoBuilder dependency.
"""

from __future__ import annotations

import asyncio
import hashlib
import io

from PIL import Image
from sqlalchemy.orm import Session

from config import (
    DEFAULT_SCENE_TEXT_FONT,
    FONTS_DIR,
    MAX_PREVIEW_IMAGE_BYTES,
    TTS_CACHE_DIR,
    TTS_DEFAULT_SEED,
    TTS_MAX_NEW_TOKENS_BASE,
    TTS_MAX_NEW_TOKENS_CAP,
    TTS_MAX_NEW_TOKENS_PER_CHAR,
    TTS_PREVIEW_BATCH_CONCURRENCY,
    TTS_REPETITION_PENALTY,
    TTS_TEMPERATURE,
    TTS_TOP_P,
    logger,
)
from schemas import (
    BatchTTSPreviewItem,
    BatchTTSPreviewRequest,
    BatchTTSPreviewResponse,
    FrameLayoutInfo,
    PreValidateIssue,
    PreValidateRequest,
    PreValidateResponse,
    SceneFramePreviewRequest,
    SceneFramePreviewResponse,
    SceneTTSPreviewRequest,
    SceneTTSPreviewResponse,
    TimelineRequest,
    TimelineResponse,
    TimelineSceneOutput,
)
from services.asset_service import AssetService
from services.storage import get_storage

_TTS_BATCH_SEMAPHORE = asyncio.Semaphore(TTS_PREVIEW_BATCH_CONCURRENCY)


# ── TTS Preview ──────────────────────────────────────────


async def preview_scene_tts(
    req: SceneTTSPreviewRequest,
    db: Session,
) -> SceneTTSPreviewResponse:
    """Generate TTS preview for a single scene. Cache-compatible with render pipeline."""
    from services.audio_client import synthesize_tts
    from services.video.tts_helpers import (
        get_preset_voice_info,
        get_speaker_voice_preset,
        translate_voice_prompt,
        tts_cache_key,
    )
    from services.video.utils import clean_script_for_tts, has_speakable_content

    script = req.script.strip()
    if not script or not has_speakable_content(script):
        raise ValueError("스크립트에 TTS로 변환할 내용이 없습니다.")

    cleaned = clean_script_for_tts(script)

    # Resolve voice preset
    voice_preset_id = req.voice_preset_id
    if not voice_preset_id and req.storyboard_id:
        voice_preset_id = get_speaker_voice_preset(req.storyboard_id, req.speaker)

    # Resolve voice design + seed
    voice_design = req.voice_design_prompt
    voice_seed: int | None = None

    if voice_preset_id:
        preset_prompt, preset_seed = get_preset_voice_info(voice_preset_id)
        if not voice_design and preset_prompt:
            voice_design = preset_prompt
        if preset_seed is not None:
            voice_seed = preset_seed

    # Apply scene emotion to voice design
    if req.scene_emotion and req.scene_emotion.strip():
        voice_design = (
            f"{voice_design}, {req.scene_emotion}" if voice_design else req.scene_emotion
        )

    if voice_design:
        voice_design = translate_voice_prompt(voice_design)

    if voice_seed is None:
        voice_seed = TTS_DEFAULT_SEED

    # Build cache key (identical to render pipeline)
    cache_key = tts_cache_key(cleaned, voice_preset_id, voice_design, req.language)
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"

    # Check cache
    if cache_path.exists():
        audio_bytes = cache_path.read_bytes()
        asset = _save_audio_asset(db, audio_bytes, cache_key)
        duration = _wav_duration(audio_bytes)
        logger.info("[Preview] TTS cache hit: %s (%.1fs)", cache_key, duration)
        return SceneTTSPreviewResponse(
            audio_url=asset.url,
            duration=duration,
            cache_key=cache_key,
            cached=True,
            voice_seed=voice_seed,
            temp_asset_id=asset.id,
        )

    # Generate TTS
    max_tokens = min(
        TTS_MAX_NEW_TOKENS_BASE + len(cleaned) * TTS_MAX_NEW_TOKENS_PER_CHAR,
        TTS_MAX_NEW_TOKENS_CAP,
    )

    audio_bytes, _sr, duration, _quality = await synthesize_tts(
        text=cleaned,
        instruct=voice_design or "",
        language=req.language,
        seed=voice_seed,
        temperature=TTS_TEMPERATURE,
        top_p=TTS_TOP_P,
        repetition_penalty=TTS_REPETITION_PENALTY,
        max_new_tokens=max_tokens,
    )

    # Save to TTS cache (same location as render pipeline)
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio_bytes)
    logger.info("[Preview] TTS generated + cached: %s (%.1fs)", cache_key, duration)

    asset = _save_audio_asset(db, audio_bytes, cache_key)

    return SceneTTSPreviewResponse(
        audio_url=asset.url,
        duration=duration,
        cache_key=cache_key,
        cached=False,
        voice_seed=voice_seed,
        temp_asset_id=asset.id,
    )


async def preview_batch_tts(
    req: BatchTTSPreviewRequest,
    db: Session,
) -> BatchTTSPreviewResponse:
    """Generate TTS previews for multiple scenes with concurrency limit."""
    items: list[BatchTTSPreviewItem] = []

    async def _process_scene(idx: int, scene_req: SceneTTSPreviewRequest):
        # Apply global fallbacks
        if req.storyboard_id and not scene_req.storyboard_id:
            scene_req.storyboard_id = req.storyboard_id
        if req.voice_preset_id and not scene_req.voice_preset_id:
            scene_req.voice_preset_id = req.voice_preset_id

        async with _TTS_BATCH_SEMAPHORE:
            try:
                result = await preview_scene_tts(scene_req, db)
                return BatchTTSPreviewItem(
                    scene_index=idx,
                    status="cached" if result.cached else "success",
                    audio_url=result.audio_url,
                    duration=result.duration,
                    cache_key=result.cache_key,
                )
            except Exception as e:
                from services.video.tts_helpers import tts_cache_key
                from services.video.utils import clean_script_for_tts

                ck = tts_cache_key(
                    clean_script_for_tts(scene_req.script) if scene_req.script.strip() else "",
                    scene_req.voice_preset_id,
                    scene_req.voice_design_prompt,
                    scene_req.language,
                )
                logger.warning("[Preview] Batch TTS failed for scene %d: %s", idx, e)
                return BatchTTSPreviewItem(
                    scene_index=idx,
                    status="failed",
                    cache_key=ck,
                    error=str(e),
                )

    tasks = [_process_scene(i, scene) for i, scene in enumerate(req.scenes)]
    results = await asyncio.gather(*tasks)

    for item in sorted(results, key=lambda x: x.scene_index):
        items.append(item)

    cached = sum(1 for i in items if i.status == "cached")
    generated = sum(1 for i in items if i.status == "success")
    failed = sum(1 for i in items if i.status == "failed")
    total_dur = sum(i.duration or 0 for i in items)

    return BatchTTSPreviewResponse(
        items=items,
        total_duration=total_dur,
        cached_count=cached,
        generated_count=generated,
        failed_count=failed,
    )


# ── Frame Preview ────────────────────────────────────────


async def preview_scene_frame(
    req: SceneFramePreviewRequest,
    db: Session,
) -> SceneFramePreviewResponse:
    """Compose a single scene frame preview (Pillow only, no FFmpeg)."""
    from services.image import (
        analyze_text_region_brightness,
        detect_face,
        load_image_bytes,
    )
    from services.rendering import (
        calculate_optimal_font_size,
        compose_post_frame,
        render_scene_text_image,
    )

    image_bytes = load_image_bytes(req.image_url)
    if len(image_bytes) > MAX_PREVIEW_IMAGE_BYTES:
        raise ValueError(
            f"이미지 크기가 제한({MAX_PREVIEW_IMAGE_BYTES // (1024 * 1024)}MB)을 초과합니다."
        )
    font_name = req.scene_text_font or DEFAULT_SCENE_TEXT_FONT
    font_path = str(FONTS_DIR / font_name)

    layout_info = FrameLayoutInfo()

    if req.layout_style == "post":
        frame = compose_post_frame(
            image_bytes=image_bytes,
            width=req.width,
            height=req.height,
            channel_name=req.channel_name or "",
            caption=req.caption or "",
            subtitle_text=req.script if req.include_scene_text else "",
            font_path=font_path,
        )
        # Detect face info for layout_info
        src_img = Image.open(io.BytesIO(image_bytes))
        face = detect_face(src_img)
        layout_info.face_detected = face is not None
        src_img.close()

    else:
        # Full layout: image + scene text overlay
        src_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        frame = src_img.resize((req.width, req.height), Image.LANCZOS)

        if req.include_scene_text and req.script.strip():
            lines = req.script.strip().split("\n")
            font_size = calculate_optimal_font_size(req.script, 40)
            layout_info.font_size = font_size

            brightness = analyze_text_region_brightness(frame, 0.85)
            layout_info.text_brightness = brightness

            text_overlay = render_scene_text_image(
                lines=lines,
                width=req.width,
                height=req.height,
                font_path=font_path,
                use_post_layout=False,
                post_layout_metrics=None,
                font_size_override=font_size,
                background_image=frame,
            )
            frame.paste(text_overlay, (0, 0), text_overlay)
            text_overlay.close()

        src_img.close()

    # Save to storage
    buf = io.BytesIO()
    frame.convert("RGB").save(buf, format="PNG")
    frame.close()
    png_bytes = buf.getvalue()

    digest = hashlib.sha256(png_bytes).hexdigest()[:16]
    file_name = f"frame_preview_{digest}.png"
    storage_key = f"previews/frames/{file_name}"

    storage = get_storage()
    storage.save(storage_key, png_bytes, content_type="image/png")

    asset_svc = AssetService(db)
    asset = asset_svc.register_asset(
        file_name=file_name,
        file_type="image",
        storage_key=storage_key,
        owner_type="frame_preview",
        is_temp=True,
        file_size=len(png_bytes),
        mime_type="image/png",
        checksum=AssetService.compute_checksum(png_bytes),
    )

    return SceneFramePreviewResponse(
        preview_url=asset.url,
        temp_asset_id=asset.id,
        layout_info=layout_info,
    )


# ── Timeline ─────────────────────────────────────────────


def preview_timeline(req: TimelineRequest) -> TimelineResponse:
    """Calculate timeline data for all scenes."""
    from services.video.utils import calculate_speed_params, has_speakable_content

    transition_dur, tts_padding, clamped_speed = calculate_speed_params(req.speed_multiplier)

    scenes_out: list[TimelineSceneOutput] = []
    cumulative = 0.0

    for i, scene in enumerate(req.scenes):
        has_tts = has_speakable_content(scene.script) if scene.script.strip() else False
        tts_dur = scene.tts_duration

        if has_tts and tts_dur and tts_dur > 0:
            xfade_tail = transition_dur if i < len(req.scenes) - 1 else 0.0
            effective = max(
                scene.duration / clamped_speed,
                transition_dur + tts_dur + tts_padding + xfade_tail,
            )
        else:
            effective = scene.duration / clamped_speed

        start = cumulative
        end = cumulative + effective
        cumulative = end

        scenes_out.append(
            TimelineSceneOutput(
                scene_index=i,
                effective_duration=round(effective, 2),
                tts_duration=round(tts_dur, 2) if tts_dur else None,
                has_tts=has_tts,
                start_time=round(start, 2),
                end_time=round(end, 2),
            )
        )

    return TimelineResponse(
        scenes=scenes_out,
        total_duration=round(cumulative, 2),
    )


# ── Pre-validation ───────────────────────────────────────


async def preview_validate(
    req: PreValidateRequest,
    db: Session,
) -> PreValidateResponse:
    """Run pre-render validation checks on a storyboard."""
    from models.storyboard import Storyboard
    from services.video.tts_helpers import tts_cache_key
    from services.video.utils import clean_script_for_tts, has_speakable_content

    storyboard = db.get(Storyboard, req.storyboard_id)
    if not storyboard or storyboard.deleted_at is not None:
        raise ValueError("스토리보드를 찾을 수 없습니다.")

    scenes = sorted(
        [s for s in storyboard.scenes if s.deleted_at is None],
        key=lambda s: s.order,
    )
    issues: list[PreValidateIssue] = []
    cached_tts = 0

    if not scenes:
        issues.append(
            PreValidateIssue(
                level="error",
                scene_index=None,
                category="scenes",
                message="씬이 없습니다.",
            )
        )
        return PreValidateResponse(
            is_ready=False,
            issues=issues,
            total_scenes=0,
        )

    for i, scene in enumerate(scenes):
        # Image check
        if not scene.image_asset_id and not _scene_has_image(scene):
            issues.append(
                PreValidateIssue(
                    level="error",
                    scene_index=i,
                    category="image",
                    message=f"씬 {i + 1}: 이미지가 없습니다.",
                )
            )

        # Script check
        script = scene.script or ""
        if not script.strip():
            issues.append(
                PreValidateIssue(
                    level="warning",
                    scene_index=i,
                    category="script",
                    message=f"씬 {i + 1}: 스크립트가 비어있습니다.",
                )
            )
        elif len(script) > 500:
            issues.append(
                PreValidateIssue(
                    level="warning",
                    scene_index=i,
                    category="script",
                    message=f"씬 {i + 1}: 스크립트가 매우 깁니다 ({len(script)}자).",
                )
            )

        # TTS cache check
        if has_speakable_content(script):
            cleaned = clean_script_for_tts(script)
            ck = tts_cache_key(cleaned, None, None, "korean")
            cache_path = TTS_CACHE_DIR / f"{ck}.wav"
            if cache_path.exists():
                cached_tts += 1
            else:
                issues.append(
                    PreValidateIssue(
                        level="info",
                        scene_index=i,
                        category="tts",
                        message=f"씬 {i + 1}: TTS 캐시 없음 (렌더링 시 생성됩니다).",
                    )
                )

    # Total duration estimate
    total_dur = sum((s.duration or 3.0) for s in scenes)
    if total_dur > 60:
        issues.append(
            PreValidateIssue(
                level="warning",
                scene_index=None,
                category="duration",
                message=f"예상 영상 길이가 {total_dur:.0f}초로 60초를 초과합니다.",
            )
        )

    has_errors = any(issue.level == "error" for issue in issues)

    return PreValidateResponse(
        is_ready=not has_errors,
        issues=issues,
        total_duration=round(total_dur, 2),
        cached_tts_count=cached_tts,
        total_scenes=len(scenes),
    )


# ── Helpers ──────────────────────────────────────────────


def _save_audio_asset(db: Session, audio_bytes: bytes, cache_key: str):
    """Save audio bytes to storage and register as temp asset."""
    digest = hashlib.sha256(audio_bytes).hexdigest()[:16]
    file_name = f"tts_preview_{digest}.wav"
    storage_key = f"previews/tts/{file_name}"

    storage = get_storage()
    storage.save(storage_key, audio_bytes, content_type="audio/wav")

    asset_svc = AssetService(db)
    return asset_svc.register_asset(
        file_name=file_name,
        file_type="audio",
        storage_key=storage_key,
        owner_type="tts_preview",
        is_temp=True,
        file_size=len(audio_bytes),
        mime_type="audio/wav",
        checksum=AssetService.compute_checksum(audio_bytes),
    )


def _wav_duration(wav_bytes: bytes) -> float:
    """Calculate duration of WAV audio from bytes."""
    import wave

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate if rate > 0 else 0.0


def _scene_has_image(scene) -> bool:
    """Check if scene has any image source."""
    candidates = scene.candidates or []
    return bool(candidates and any(c.get("media_asset_id") for c in candidates))
