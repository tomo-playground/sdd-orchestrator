"""Scene processing for the video pipeline.

Handles per-scene image loading, TTS generation, subtitle text wrapping,
and post-layout image composition. Each function receives the VideoBuilder
instance as its first argument.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from config import (
    DEFAULT_SPEAKER,
    STORAGE_MODE,
    TTS_CACHE_DIR,
    TTS_DEFAULT_LANGUAGE,
    TTS_DEFAULT_SEED,
    TTS_MAX_NEW_TOKENS_BASE,
    TTS_MAX_NEW_TOKENS_CAP,
    TTS_MAX_NEW_TOKENS_PER_CHAR,
    TTS_MAX_RETRIES,
    TTS_MIN_DURATION_SEC,
    TTS_REPETITION_PENALTY,
    TTS_TEMPERATURE,
    TTS_TOP_P,
    TTS_VOICE_CONSISTENCY_MODE,
    logger,
)
from services.audio_client import record_scene_failure as _audio_scene_failure
from services.audio_client import record_scene_success as _audio_scene_success
from services.audio_client import synthesize_tts as _audio_synthesize_tts
from services.storage import get_storage
from services.video.tts_helpers import (
    generate_context_aware_voice_prompt,
    get_preset_voice_info,
    get_speaker_voice_preset,
    translate_voice_prompt,
    tts_cache_key,
)
from services.video.utils import clean_script_for_tts, has_speakable_content

if TYPE_CHECKING:
    from schemas import VideoScene
    from services.video.builder import VideoBuilder

_translate_voice_prompt = translate_voice_prompt  # noqa: F841 — alias for voice_presets.py
_get_speaker_voice_preset = get_speaker_voice_preset  # noqa: F841 — alias for tests


def _atomic_cache_write(src: Path, dst: Path) -> None:
    """Copy *src* to *dst* atomically (same filesystem rename)."""
    import os
    import tempfile

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dst.parent, suffix=".tmp")
    try:
        os.close(tmp_fd)
        shutil.copy2(src, tmp_path)
        os.replace(tmp_path, dst)  # atomic on same filesystem
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


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


def _resolve_voice_preset_id(
    builder: VideoBuilder,
    scene_idx: int,
) -> int | None:
    """Resolve voice_preset_id for a scene following priority:

    1. Speaker-specific preset (Character -> character.voice_preset_id)
    2. VideoRequest.voice_preset_id   (global render panel preset)

    Note: per-scene voice_design_prompt does NOT bypass preset lookup.
    Seed must always come from the preset; voice design text is handled
    separately in _get_voice_design_for_scene.
    """
    scene_req = builder.request.scenes[scene_idx]

    # Speaker-specific preset (seed must always come from preset, even if scene has voice_design_prompt)
    # voice_design text priority is handled separately in _get_voice_design_for_scene
    speaker = scene_req.speaker or DEFAULT_SPEAKER
    logger.debug(f"[TTS] Scene {scene_idx}: speaker='{speaker}', storyboard_id={builder.request.storyboard_id}")
    speaker_preset = get_speaker_voice_preset(
        builder.request.storyboard_id,
        speaker,
    )
    if speaker_preset:
        logger.info(f"[TTS] Scene {scene_idx}: using speaker-specific preset {speaker_preset}")
        return speaker_preset

    # Global fallback
    logger.info(f"[TTS] Scene {scene_idx}: falling back to global preset {builder.request.voice_preset_id}")
    return builder.request.voice_preset_id


def _calculate_max_new_tokens(text: str) -> int:
    """텍스트 길이 기반 동적 max_new_tokens. Qwen3-TTS 12Hz 기준 안전 마진."""
    dynamic = len(text) * TTS_MAX_NEW_TOKENS_PER_CHAR
    return min(max(dynamic, TTS_MAX_NEW_TOKENS_BASE), TTS_MAX_NEW_TOKENS_CAP)


async def generate_tts(
    builder: VideoBuilder,
    i: int,
    clean_script: str,
    tts_path: Path,
) -> tuple[bool, float]:
    """Generate TTS audio for a scene using VoiceDesign model.

    Uses voice_design_prompt + seed for consistent voice generation.
    If voice_preset_id is set, loads prompt/seed from DB.
    Results are cached by hash(clean_script + voice_config) to skip regeneration.
    """
    if not clean_script.strip():
        logger.warning(f"Scene {i}: empty script, skipping TTS")
        return False, 0.0

    task_id = builder.project_id
    scene_req = builder.request.scenes[i]

    # --- Linked TTS preview asset: skip generation if valid ---
    tts_asset_id = scene_req.tts_asset_id
    if tts_asset_id is not None:
        try:
            from database import SessionLocal
            from models import MediaAsset

            db = SessionLocal()
            try:
                asset = db.get(MediaAsset, tts_asset_id)
                if not asset:
                    logger.warning(
                        "[generate_tts] tts_asset_id=%d not found in DB, falling back to generation", tts_asset_id
                    )
                elif not asset.storage_key:
                    logger.warning("[generate_tts] tts_asset_id=%d has no storage_key, falling back", tts_asset_id)
                elif asset.file_type != "audio":
                    logger.warning(
                        "[generate_tts] tts_asset_id=%d file_type=%s (not audio), falling back",
                        tts_asset_id,
                        asset.file_type,
                    )
                else:
                    storage = get_storage()
                    local = storage.get_local_path(asset.storage_key)
                    if local.exists():
                        shutil.copy2(local, tts_path)
                        tts_duration = builder._get_audio_duration(tts_path)
                        logger.info(f"Scene {i}: Using linked TTS asset {tts_asset_id}, duration={tts_duration}s")
                        _audio_scene_success(task_id)
                        return True, tts_duration
                    else:
                        logger.warning(
                            "[generate_tts] tts_asset_id=%d file not found at %s, falling back", tts_asset_id, local
                        )
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Scene {i}: Failed to load linked TTS asset {tts_asset_id}, falling back: {e}")

    # --- Resolve voice preset for this scene (speaker-aware) ---
    resolved_preset_id = _resolve_voice_preset_id(builder, i)

    # --- TTS result cache lookup ---
    voice_design_for_cache = scene_req.voice_design_prompt or builder.request.voice_design_prompt or ""
    scene_emotion = getattr(scene_req, "scene_emotion", "") or ""
    speaker = getattr(scene_req, "speaker", None) or DEFAULT_SPEAKER
    cache_key = tts_cache_key(
        clean_script,
        resolved_preset_id,
        voice_design_for_cache,
        TTS_DEFAULT_LANGUAGE,
        scene_emotion,
        speaker=speaker,
    )
    cached = TTS_CACHE_DIR / f"{cache_key}.wav"
    if cached.exists() and cached.stat().st_size > 0:
        shutil.copy2(cached, tts_path)
        tts_duration = builder._get_audio_duration(tts_path)
        logger.info(f"Scene {i}: TTS cache hit ({cache_key}), duration={tts_duration}s")
        _audio_scene_success(task_id)
        return True, tts_duration

    try:
        # Resolve voice_design_prompt and seed from preset
        preset_voice_design: str | None = None
        preset_seed: int | None = None

        if resolved_preset_id:
            preset_voice_design, preset_seed = get_preset_voice_info(
                resolved_preset_id,
            )

        voice_design = _get_voice_design_for_scene(builder, scene_req, preset_voice_design, clean_script, i)
        voice_design = translate_voice_prompt(voice_design or "")

        # Seed: preset seed > preset base prompt hash > fixed default
        # Never use per-scene voice_design for seed — it breaks voice consistency across scenes
        # hashlib.sha256 ensures deterministic result regardless of PYTHONHASHSEED
        if preset_seed:
            voice_seed = preset_seed
        elif preset_voice_design:
            voice_seed = int(hashlib.sha256(preset_voice_design.encode()).hexdigest()[:8], 16) % (2**31)
        else:
            voice_seed = TTS_DEFAULT_SEED

        # Pad very short scripts to prevent TTS model hang
        tts_text = clean_script
        if len(tts_text.strip()) < 3:
            tts_text = tts_text.strip() + "."
            logger.info(f"[TTS] Scene {i}: padded very short script '{clean_script}' -> '{tts_text}'")

        # Dynamic min duration based on script length (short scripts can't reach 1s)
        speakable_len = len(clean_script.replace(".", "").replace("!", "").replace("?", "").strip())
        if speakable_len <= 3:
            min_duration = 0.4
        elif speakable_len <= 6:
            min_duration = 0.6
        else:
            min_duration = TTS_MIN_DURATION_SEC

        logger.info(f"TTS generation: script={tts_text[:50]}..., voice_seed={voice_seed}")

        # --- Retry loop: call Audio Server → validate duration ---
        best_bytes: bytes | None = None
        best_dur = 0.0

        for attempt in range(1 + TTS_MAX_RETRIES):
            attempt_seed = voice_seed + attempt * 7919

            # Simplification logic on retries
            current_voice_design = voice_design
            if attempt == 1 and voice_design:
                logger.info(f"[TTS] Scene {i}: Attempt 2 - simplifying voice design prompt")
                current_voice_design = ", ".join((voice_design or "").split(",")[:1]).strip()
            elif attempt == 2:
                logger.info(f"[TTS] Scene {i}: Attempt 3 - using minimal voice design")
                current_voice_design = preset_voice_design or ""

            try:
                audio_bytes, _sr, duration, quality_passed = await _audio_synthesize_tts(
                    text=tts_text,
                    instruct=current_voice_design or "",
                    language=TTS_DEFAULT_LANGUAGE,
                    seed=attempt_seed,
                    temperature=TTS_TEMPERATURE,
                    top_p=TTS_TOP_P,
                    repetition_penalty=TTS_REPETITION_PENALTY,
                    max_new_tokens=_calculate_max_new_tokens(tts_text),
                    task_id=task_id,
                )
            except Exception as gen_err:
                logger.warning(
                    f"[TTS] Scene {i}: attempt {attempt + 1}/{1 + TTS_MAX_RETRIES} "
                    f"audio server error: {gen_err}, seed={attempt_seed}"
                )
                continue

            # Track best attempt (longest duration)
            if duration > best_dur:
                best_bytes, best_dur = audio_bytes, duration

            if quality_passed and duration >= min_duration:
                tts_path.write_bytes(audio_bytes)
                _atomic_cache_write(tts_path, cached)
                tts_duration = builder._get_audio_duration(tts_path)
                if attempt > 0:
                    logger.info(f"[TTS] Scene {i}: passed on attempt {attempt + 1}, duration={tts_duration:.2f}s")
                else:
                    logger.info(f"TTS success: duration={tts_duration}s, seed={attempt_seed}")
                _audio_scene_success(task_id)
                return True, tts_duration

            logger.warning(
                f"[TTS] Scene {i}: attempt {attempt + 1}/{1 + TTS_MAX_RETRIES} "
                f"failed quality/duration validation ({duration:.2f}s), seed={attempt_seed}"
            )

        if best_bytes is not None and best_dur > 0:
            tts_path.write_bytes(best_bytes)
            tts_duration = builder._get_audio_duration(tts_path)
            logger.warning(f"[TTS] Scene {i}: all retries exhausted, using best attempt ({best_dur:.2f}s, uncached)")
            _audio_scene_success(task_id)
            return True, tts_duration

        logger.warning(f"[TTS] Scene {i}: all retries exhausted with no usable audio, falling back to silent scene")
        _audio_scene_failure(task_id)
        return False, 0.0
    except Exception as e:
        logger.warning(f"[TTS] Scene {i}: unexpected error ({e}), falling back to silent scene")
        _audio_scene_failure(task_id)
        return False, 0.0


def _get_voice_design_for_scene(
    builder: VideoBuilder,
    scene_req: VideoScene,
    preset_voice_design: str | None,
    clean_script: str,
    scene_idx: int = 0,
) -> str | None:
    """Resolve the voice design prompt following the priority logic.

    Priority:
    1. preset base + scene_emotion  (preset exists → character identity preserved)
    2. scene/global voice_design_prompt  (no preset → use explicit prompt as-is)
    3. Gemini context-aware generation  (no preset, no explicit prompt)

    When a preset exists, per-scene voice_design_prompt is ignored to prevent
    Agentic Pipeline emotion prompts from overriding the character's voice identity.
    """
    from config import DEFAULT_SPEAKER

    speaker = getattr(scene_req, "speaker", DEFAULT_SPEAKER)
    scene_emotion = getattr(scene_req, "scene_emotion", None)

    # 1. Preset exists → Gemini modifies base with scene context (seed stays preset-based)
    if preset_voice_design:
        # Consistency mode: 프리셋 instruct 고정 (Gemini 감정 적응 미개입)
        if TTS_VOICE_CONSISTENCY_MODE:
            logger.info("Scene %d: Voice design (Speaker=%s): consistency mode — preset only", scene_idx, speaker)
            return preset_voice_design

        context_parts: list[str] = []
        if scene_emotion:
            context_parts.append(f"Emotion: {scene_emotion}")
        ko_prompt = getattr(scene_req, "image_prompt_ko", None)
        if ko_prompt:
            context_parts.append(ko_prompt)
        elif img_prompt := getattr(scene_req, "image_prompt", None):
            context_parts.append(img_prompt)

        context_text = ". ".join(context_parts)
        if context_text:
            voice_design = generate_context_aware_voice_prompt(
                clean_script, context_text, base_prompt=preset_voice_design
            )
            if voice_design:
                logger.info(f"Scene {scene_idx}: Voice design (Speaker={speaker}): Gemini-adapted from preset")
                return voice_design

        # Fallback: simple concatenation when Gemini unavailable or no context
        if scene_emotion:
            voice_design = f"{preset_voice_design}, {scene_emotion}"
            logger.info(f"Scene {scene_idx}: Voice design (Speaker={speaker}): base + emotion='{scene_emotion}'")
        else:
            voice_design = preset_voice_design
            logger.info(f"Scene {scene_idx}: Voice design (Speaker={speaker}): base preset only")
        return voice_design

    # 2. No preset — use explicit per-scene or global prompt
    voice_design = getattr(scene_req, "voice_design_prompt", None) or getattr(
        builder.request, "voice_design_prompt", None
    )
    if voice_design:
        logger.info(f"Scene {scene_idx}: Voice design (Speaker={speaker}): explicit prompt (no preset)")
        return voice_design

    # 3. No preset, no explicit prompt — generate via Gemini (narrator without preset)
    context_parts: list[str] = []
    if scene_emotion:
        context_parts.append(f"Emotion: {scene_emotion}")
    ko_prompt = getattr(scene_req, "image_prompt_ko", None)
    if ko_prompt:
        context_parts.append(ko_prompt)
    elif img_prompt := getattr(scene_req, "image_prompt", None):
        context_parts.append(img_prompt)

    context_text = ". ".join(context_parts)
    if context_text:
        voice_design = generate_context_aware_voice_prompt(clean_script, context_text)
        if voice_design:
            logger.info(f"Scene {scene_idx}: Auto-generated voice design (Speaker={speaker}): '{voice_design}'")
            return voice_design

    return None
