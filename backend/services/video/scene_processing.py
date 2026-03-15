"""Scene processing for the video pipeline.

Handles per-scene image loading, TTS generation, subtitle text wrapping,
and post-layout image composition. Each function receives the VideoBuilder
instance as its first argument.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from config import (
    STORAGE_MODE,
    logger,
)
from services.audio_client import record_scene_failure as _audio_scene_failure
from services.audio_client import record_scene_success as _audio_scene_success
from services.storage import get_storage
from services.video.utils import clean_script_for_tts, has_speakable_content

if TYPE_CHECKING:
    from services.video.builder import VideoBuilder


async def process_scenes(builder: VideoBuilder) -> None:
    """Process all scenes: images, TTS, and subtitles."""
    from services.video.progress import calc_overall_percent

    tts_failed_scenes: list[int] = []

    for i, scene in enumerate(builder.request.scenes):
        if builder._progress:
            builder._progress.current_scene = i + 1
            builder._progress.message = f"Scene {i + 1}/{builder.num_scenes} TTS"
            builder._progress.percent = calc_overall_percent(builder._progress)
            builder._progress.notify()

        img_path = builder.temp_dir / f"scene_{i}.png"
        tts_path = builder.temp_dir / f"tts_{i}.mp3"

        # Load image bytes from storage or URL
        image_bytes = _load_scene_image(builder, scene.image_url)

        raw_script = scene.script or ""
        logger.info(f"Scene {i}: script='{raw_script}', len={len(raw_script)}")
        clean_script = clean_script_for_tts(raw_script)

        # Process subtitles FIRST (before post layout)
        if builder.request.include_scene_text:
            lines, font_size = wrap_scene_text(builder, clean_script)
            builder.subtitle_lines.append(lines)
            builder.scene_text_font_sizes.append(font_size)
        else:
            builder.subtitle_lines.append([])
            builder.scene_text_font_sizes.append(0)

        # Apply post layout (now subtitle_lines[i] is available)
        if builder.use_post_layout:
            process_post_layout_image(builder, i, image_bytes, img_path)
        else:
            img_path.write_bytes(image_bytes)

        # Gate TTS: only generate for scenes with speakable content
        if has_speakable_content(raw_script):
            has_valid_tts, tts_duration = await generate_tts(
                builder,
                i,
                clean_script,
                tts_path,
            )
            if not has_valid_tts:
                tts_failed_scenes.append(i)
        else:
            logger.info(f"Scene {i}: no speakable content ('{raw_script[:30]}'), skipping TTS")
            has_valid_tts, tts_duration = False, 0.0

        # Add to input args
        builder.input_args.extend(["-loop", "1", "-i", str(img_path)])
        if has_valid_tts:
            builder.input_args.extend(["-i", str(tts_path)])
        else:
            # Limit anullsrc duration to prevent infinite stream / memory leak.
            # Use scene duration hint + generous padding; exact trim happens later
            # in build_audio_filters via atrim.
            scene_dur_hint = (getattr(scene, "duration", 3) or 3) / builder.speed_multiplier
            silent_limit = scene_dur_hint + builder.transition_dur + 2.0
            builder.input_args.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    str(silent_limit),
                    "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={silent_limit}",
                ]
            )

        builder.tts_valid.append(has_valid_tts)
        builder.tts_durations.append(tts_duration)

    if tts_failed_scenes:
        logger.warning(
            "[process_scenes] TTS failed for %d/%d scenes: indices=%s",
            len(tts_failed_scenes),
            builder.num_scenes,
            tts_failed_scenes,
        )


def _load_scene_image(builder: VideoBuilder, img_src: str | None) -> bytes:
    """Load scene image bytes from storage or URL fallback."""
    if img_src and ("/projects/" in img_src or (STORAGE_MODE == "s3" and "shorts-producer" in img_src)):
        try:
            if "projects/" in img_src:
                storage_key = "projects/" + img_src.split("projects/", 1)[1]
                storage = get_storage()
                local_path = storage.get_local_path(storage_key)
                image_bytes = local_path.read_bytes()
                logger.info("[Video Build] Loaded image from storage: %s", storage_key)
                return image_bytes
            return builder._load_image_bytes(img_src)
        except Exception as e:
            logger.warning(
                "[Video Build] Failed to load from storage, fallback to URL: %s",
                e,
            )
            return builder._load_image_bytes(img_src)
    return builder._load_image_bytes(img_src)


def wrap_scene_text(builder: VideoBuilder, text: str) -> tuple[list[str], int]:
    """Wrap subtitle text based on font pixel width with dynamic font sizing.

    Calculates max width and font size based on layout type,
    then wraps text to fit within the available space.
    If text doesn't fit, reduces font size until it fits or minimum is reached.

    Returns:
        Tuple of (lines, font_size)
    """
    from PIL import ImageFont

    if not text:
        return [], 0

    # Determine font size range and max width based on layout
    if builder.use_post_layout:
        base_font_size = int(builder.out_h * builder._PostLayout.SUBTITLE_FONT_RATIO)
        min_font_size = int(builder.out_h * builder._PostLayout.SUBTITLE_MIN_FONT_RATIO)
        if builder.post_layout_metrics:
            card_w = builder.post_layout_metrics["card_width"]
            card_p = builder.post_layout_metrics["card_padding"]
            text_area_width = card_w - (card_p * 2)
        else:
            card_w = int(builder.out_w * builder._PostLayout.CARD_WIDTH_RATIO)
            card_p = int(card_w * builder._PostLayout.CARD_PADDING_RATIO)
            text_area_width = card_w - (card_p * 2)
        max_width_px = int(text_area_width * builder._PostLayout.SUBTITLE_MAX_WIDTH_RATIO)
        max_lines = builder._PostLayout.SUBTITLE_MAX_LINES
    else:
        base_font_size = int(builder.out_h * builder._FullLayout.SUBTITLE_FONT_RATIO)
        min_font_size = int(builder.out_h * builder._FullLayout.SUBTITLE_MIN_FONT_RATIO)
        max_width_px = int(builder.out_w * builder._FullLayout.SUBTITLE_MAX_WIDTH_RATIO)
        max_lines = builder._FullLayout.SUBTITLE_MAX_LINES

    # Try wrapping with decreasing font sizes
    font_size = base_font_size
    font_step = 2

    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(builder.font_path, font_size)
        except Exception:
            logger.warning("Font loading failed, using character-based wrapping")
            wrapped = builder._wrap_text(text, width=20, max_lines=max_lines)
            lines = [line for line in wrapped.splitlines() if line.strip()]
            return lines, base_font_size

        lines = builder._wrap_text_by_font(text, font, max_width_px, max_lines)

        if len(lines) <= max_lines:
            all_fit = all(not (bbox := font.getbbox(line)) or (bbox[2] - bbox[0]) <= max_width_px for line in lines)
            if all_fit:
                if font_size < base_font_size:
                    logger.info(f"Dynamic font: {base_font_size}px -> {font_size}px for text: {text[:30]}...")
                return lines, font_size

        font_size -= font_step

    # Minimum font size reached, return best effort
    try:
        font = ImageFont.truetype(builder.font_path, min_font_size)
        lines = builder._wrap_text_by_font(text, font, max_width_px, max_lines)
        logger.warning(f"Using minimum font size {min_font_size}px for: {text[:30]}...")
        return lines, min_font_size
    except Exception:
        wrapped = builder._wrap_text(text, width=20, max_lines=max_lines)
        lines = [line for line in wrapped.splitlines() if line.strip()]
        return lines, base_font_size


def process_post_layout_image(
    builder: VideoBuilder,
    i: int,
    image_bytes: bytes,
    img_path: Path,
) -> None:
    """Process image for post layout."""
    try:
        overlay_settings = builder.request.overlay_settings or builder._OverlaySettings()
        post_settings = builder.request.post_card_settings or builder._PostCardSettings(
            channel_name=overlay_settings.channel_name,
            avatar_key=overlay_settings.avatar_key,
            caption=overlay_settings.caption,
        )
        subtitle_text = "\n".join(builder.subtitle_lines[i]) if builder.subtitle_lines[i] else ""
        composed = builder._compose_post_frame(
            image_bytes,
            builder.out_w,
            builder.out_h,
            post_settings.channel_name,
            post_settings.caption,
            subtitle_text,
            builder.font_path,
            builder.post_avatar_file or builder.avatar_file,
            builder._post_views,
            builder._post_time,
        )
        composed.save(img_path, "PNG")
    except Exception:
        img_path.write_bytes(image_bytes)


async def generate_tts(
    builder: VideoBuilder,
    i: int,
    clean_script: str,
    tts_path: Path,
) -> tuple[bool, float]:
    """tts_asset_id로 사전 생성된 TTS를 로드한다. 생성 로직 없음.

    TTS 생성은 prebuild 단계(tts_prebuild.py → generate_tts_audio)에서 수행한다.
    tts_asset_id가 없으면 무음 처리한다.
    """
    if not clean_script.strip():
        logger.warning("Scene %d: empty script, skipping TTS", i)
        return False, 0.0

    task_id = builder.project_id
    scene_req = builder.request.scenes[i]
    tts_asset_id = scene_req.tts_asset_id

    if tts_asset_id is not None:
        try:
            from database import SessionLocal  # noqa: PLC0415
            from models import MediaAsset  # noqa: PLC0415

            db = SessionLocal()
            try:
                asset = db.get(MediaAsset, tts_asset_id)
                if not asset:
                    logger.warning("[generate_tts] tts_asset_id=%d not found in DB", tts_asset_id)
                elif not asset.storage_key:
                    logger.warning("[generate_tts] tts_asset_id=%d has no storage_key", tts_asset_id)
                elif asset.file_type != "audio":
                    logger.warning(
                        "[generate_tts] tts_asset_id=%d file_type=%s (not audio)", tts_asset_id, asset.file_type
                    )
                else:
                    if asset.is_temp:
                        asset.is_temp = False
                        db.commit()
                        logger.info("[TTS] Promoted tts_asset_id=%d to permanent", tts_asset_id)
                    storage = get_storage()
                    local = storage.get_local_path(asset.storage_key)
                    if local.exists():
                        shutil.copy2(local, tts_path)
                        tts_duration = builder._get_audio_duration(tts_path)
                        logger.info(
                            "Scene %d: Using linked TTS asset %d, duration=%.2fs", i, tts_asset_id, tts_duration
                        )
                        _audio_scene_success(task_id)
                        return True, tts_duration
                    logger.warning("[generate_tts] tts_asset_id=%d file not found at %s", tts_asset_id, local)
            finally:
                db.close()
        except Exception as e:
            logger.warning("Scene %d: Failed to load linked TTS asset %d: %s", i, tts_asset_id, e)

    # tts_asset_id 없음 → 무음 처리 (prebuild 미실행 또는 실패)
    logger.warning("Scene %d: tts_asset_id 없음 — 무음 처리 (tts-prebuild를 먼저 실행하세요)", i)
    _audio_scene_failure(task_id)
    return False, 0.0
