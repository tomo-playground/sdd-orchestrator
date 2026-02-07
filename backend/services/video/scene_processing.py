"""Scene processing for the video pipeline.

Handles per-scene image loading, TTS generation, subtitle text wrapping,
and post-layout image composition. Each function receives the VideoBuilder
instance as its first argument.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

# Eager-loaded TTS dependencies (torch + qwen_tts)
# TTS is required for video rendering with voice narration.
import torch as _torch
from qwen_tts import Qwen3TTSModel as _Qwen3TTSModel

from config import (
    DEFAULT_SPEAKER,
    GEMINI_TEXT_MODEL,
    STORAGE_MODE,
    TTS_ATTN_IMPLEMENTATION,
    TTS_CACHE_DIR,
    TTS_DEFAULT_LANGUAGE,
    TTS_DEVICE,
    TTS_MODEL_NAME,
    TTS_REPETITION_PENALTY,
    TTS_TEMPERATURE,
    TTS_TIMEOUT_SECONDS,
    TTS_TOP_P,
    gemini_client,
    logger,
)
from services.storage import get_storage
from services.video.utils import clean_script_for_tts

_TTS_AVAILABLE = True


def _ensure_tts_deps() -> bool:
    """Check TTS availability. Always returns True with eager loading."""
    return _TTS_AVAILABLE


# Global model cache for Qwen-TTS (single model swap)
_current_model = None
_current_model_type: str | None = None
_model_lock = asyncio.Lock()

# Simple cache: Korean prompt → English translation
_VOICE_PROMPT_CACHE: dict[str, str] = {}
_HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def _tts_cache_key(text: str, voice_preset_id: int | None, voice_design_prompt: str | None, language: str) -> str:
    """Deterministic hash for TTS caching based on text + voice config."""
    parts = f"{text}|{voice_preset_id}|{voice_design_prompt or ''}|{language}"
    return hashlib.sha256(parts.encode()).hexdigest()[:16]


def _resolve_device() -> str:
    device = TTS_DEVICE
    if device == "auto":
        device = "mps" if _torch.backends.mps.is_available() else "cpu"
    return device


def _load_model(model_name: str):
    """Load a Qwen-TTS model (blocking). Requires _ensure_tts_deps() first."""
    device = _resolve_device()
    logger.info(f"Loading Qwen-TTS model ({model_name}) on {device}...")
    model = _Qwen3TTSModel.from_pretrained(
        model_name,
        dtype=_torch.bfloat16 if device == "mps" else _torch.float32,
        attn_implementation=TTS_ATTN_IMPLEMENTATION,
    )
    model.model.to(device)
    model.device = _torch.device(device)
    return model


def get_qwen_model():
    """Synchronous model getter (for lifespan preload). Always loads VoiceDesign model."""
    global _current_model, _current_model_type
    if not _ensure_tts_deps():
        raise RuntimeError("TTS dependencies unavailable (torch/qwen_tts)")
    if _current_model is None:
        _current_model = _load_model(TTS_MODEL_NAME)
        _current_model_type = "voice_design"
    return _current_model


async def get_qwen_model_async():
    """Async model getter. Loads VoiceDesign model if not already loaded."""
    global _current_model, _current_model_type
    if not _ensure_tts_deps():
        raise RuntimeError("TTS dependencies unavailable (torch/qwen_tts)")
    async with _model_lock:
        if _current_model is not None:
            return _current_model
        loop = asyncio.get_event_loop()
        _current_model = await loop.run_in_executor(None, _load_model, TTS_MODEL_NAME)
        _current_model_type = "voice_design"
        return _current_model


def _translate_voice_prompt(prompt: str) -> str:
    """Translate Korean voice design prompt to English via Gemini."""
    if not prompt or not _HANGUL_RE.search(prompt):
        return prompt
    if prompt in _VOICE_PROMPT_CACHE:
        return _VOICE_PROMPT_CACHE[prompt]
    if not gemini_client:
        logger.warning("[TTS] No Gemini client, skipping voice prompt translation")
        return prompt
    try:
        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=(
                "Translate the following Korean TTS voice description to English. "
                "Return ONLY the translated text, nothing else.\n\n"
                f"{prompt}"
            ),
        )
        translated = res.text.strip()
        _VOICE_PROMPT_CACHE[prompt] = translated
        logger.info(f"[TTS] Voice prompt translated: '{prompt}' → '{translated}'")
        return translated
    except Exception as e:
        logger.warning(f"[TTS] Voice prompt translation failed: {e}")
        return prompt


if TYPE_CHECKING:
    from services.video.builder import VideoBuilder


async def process_scenes(builder: VideoBuilder) -> None:
    """Process all scenes: images, TTS, and subtitles."""
    from services.video.progress import calc_overall_percent

    for i, scene in enumerate(builder.request.scenes):
        if builder._progress:
            builder._progress.current_scene = i + 1
            builder._progress.stage_detail = f"Scene {i + 1}/{builder.num_scenes} TTS"
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

        # Generate TTS (use cleaned script for better pronunciation)
        has_valid_tts, tts_duration = await generate_tts(
            builder,
            i,
            clean_script,
            tts_path,
        )

        # Add to input args
        builder.input_args.extend(["-loop", "1", "-i", str(img_path)])
        if has_valid_tts:
            builder.input_args.extend(["-i", str(tts_path)])
        else:
            builder.input_args.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            )

        builder.tts_valid.append(has_valid_tts)
        builder.tts_durations.append(tts_duration)


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
            logger.warning("[Video Build] Failed to load from storage, fallback to URL: %s", e)
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


def process_post_layout_image(builder: VideoBuilder, i: int, image_bytes: bytes, img_path: Path) -> None:
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


def _get_preset_voice_info(voice_preset_id: int) -> tuple[str | None, int | None]:
    """Fetch voice_design_prompt and voice_seed from a voice preset."""
    from database import get_db
    from models.voice_preset import VoicePreset

    db = next(get_db())
    try:
        preset = db.get(VoicePreset, voice_preset_id)
        if not preset:
            return None, None
        prompt = preset.voice_design_prompt
        seed = preset.voice_seed
        if prompt:
            logger.info(f"[TTS] Preset {voice_preset_id}: prompt='{prompt[:40]}', seed={seed}")
        return prompt, seed
    except Exception as e:
        logger.error(f"[TTS] Failed to get preset voice info: {e}")
        return None, None
    finally:
        db.close()


def _get_speaker_voice_preset(storyboard_id: int | None, speaker: str) -> int | None:
    """Resolve speaker to a voice_preset_id from Storyboard/Character.

    - "Narrator" -> Storyboard.narrator_voice_preset_id
    - Character name (e.g. "A") -> Character.voice_preset_id
      looked up via character_id on the storyboard.
    """
    if not storyboard_id:
        logger.debug("[TTS] _get_speaker_voice_preset: no storyboard_id, returning None")
        return None

    from database import get_db
    from models.character import Character
    from models.group import Group
    from models.storyboard import Storyboard
    from services.config_resolver import resolve_effective_config

    db = next(get_db())
    try:
        storyboard = db.get(Storyboard, storyboard_id)
        if not storyboard:
            return None

        # Resolve effective config via cascade
        group = db.get(Group, storyboard.group_id) if storyboard.group_id else None
        effective = resolve_effective_config(group.project, group) if group else {"values": {}}

        if speaker == DEFAULT_SPEAKER:
            preset_id = effective["values"].get("narrator_voice_preset_id")
            if preset_id:
                logger.info(f"[TTS] Narrator voice preset from cascade: {preset_id}")
                return preset_id
            return None

        # Non-narrator speaker -> resolve via storyboard_characters first, then fallback to cascade
        from services.speaker_resolver import resolve_speaker_to_character

        resolved_char_id = resolve_speaker_to_character(storyboard_id, speaker, db)
        if not resolved_char_id:
            logger.warning(
                f"[TTS] No character mapping for speaker '{speaker}' in storyboard {storyboard_id}. "
                f"Falling back to default voice."
            )
            return None
        char = db.get(Character, resolved_char_id)
        if char and char.voice_preset_id:
            logger.info(
                f"[TTS] Speaker '{speaker}' voice preset from character {char.name}({resolved_char_id}): {char.voice_preset_id}"
            )
            return char.voice_preset_id
        return None
    except Exception as e:
        logger.error(f"[TTS] Failed to resolve speaker voice preset: {e}")
        return None
    finally:
        db.close()


def _resolve_voice_preset_id(
    builder: VideoBuilder,
    scene_idx: int,
) -> int | None:
    """Resolve voice_preset_id for a scene following priority:

    1. scene_req.voice_design_prompt  (per-scene override — skip preset lookup)
    2. Speaker-specific preset (Narrator -> storyboard, Character -> character)
    3. VideoRequest.voice_preset_id   (global render panel preset)
    """
    scene_req = builder.request.scenes[scene_idx]

    # 1. Per-scene voice_design_prompt overrides everything
    if scene_req.voice_design_prompt:
        logger.debug(f"[TTS] Scene {scene_idx}: using per-scene voice_design_prompt, skipping preset")
        return None

    # 2. Speaker-specific preset
    speaker = scene_req.speaker or DEFAULT_SPEAKER
    logger.debug(f"[TTS] Scene {scene_idx}: speaker='{speaker}', storyboard_id={builder.request.storyboard_id}")
    speaker_preset = _get_speaker_voice_preset(
        builder.request.storyboard_id,
        speaker,
    )
    if speaker_preset:
        logger.info(f"[TTS] Scene {scene_idx}: using speaker-specific preset {speaker_preset}")
        return speaker_preset

    # 3. Global fallback
    logger.info(f"[TTS] Scene {scene_idx}: falling back to global preset {builder.request.voice_preset_id}")
    return builder.request.voice_preset_id


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

    scene_req = builder.request.scenes[i]

    # --- Resolve voice preset for this scene (speaker-aware) ---
    resolved_preset_id = _resolve_voice_preset_id(builder, i)

    # --- TTS result cache lookup ---
    voice_design_for_cache = scene_req.voice_design_prompt or builder.request.voice_design_prompt or ""
    cache_key = _tts_cache_key(
        clean_script,
        resolved_preset_id,
        voice_design_for_cache,
        TTS_DEFAULT_LANGUAGE,
    )
    cached = TTS_CACHE_DIR / f"{cache_key}.mp3"
    if cached.exists() and cached.stat().st_size > 0:
        shutil.copy2(cached, tts_path)
        tts_duration = builder._get_audio_duration(tts_path)
        logger.info(f"Scene {i}: TTS cache hit ({cache_key}), duration={tts_duration}s")
        return True, tts_duration

    try:
        # Resolve voice_design_prompt and seed from preset
        preset_voice_design: str | None = None
        preset_seed: int | None = None

        if resolved_preset_id:
            preset_voice_design, preset_seed = _get_preset_voice_info(
                resolved_preset_id,
            )

        voice_design = scene_req.voice_design_prompt or preset_voice_design or builder.request.voice_design_prompt
        voice_design = _translate_voice_prompt(voice_design or "")

        # Seed: preset seed > hash-based fallback
        voice_seed = preset_seed or (hash(voice_design or "") % (2**31))

        logger.info(f"TTS generation (VoiceDesign): script={clean_script[:50]}..., voice_seed={voice_seed}")
        model = await get_qwen_model_async()

        import soundfile as sf

        loop = asyncio.get_event_loop()

        def _voice_design():
            _torch.manual_seed(voice_seed)
            return model.generate_voice_design(
                text=clean_script,
                instruct=voice_design or "",
                language=TTS_DEFAULT_LANGUAGE,
                temperature=TTS_TEMPERATURE,
                top_p=TTS_TOP_P,
                repetition_penalty=TTS_REPETITION_PENALTY,
            )

        logger.info(f"Scene {i}: voice design — '{(voice_design or '')[:40]}'")
        wavs, sr = await asyncio.wait_for(
            loop.run_in_executor(None, _voice_design),
            timeout=TTS_TIMEOUT_SECONDS,
        )

        sf.write(str(tts_path), wavs[0], sr)

        if tts_path.exists() and tts_path.stat().st_size > 0:
            shutil.copy2(tts_path, cached)
            tts_duration = builder._get_audio_duration(tts_path)
            logger.info(f"TTS success (VoiceDesign): duration={tts_duration}s, seed={voice_seed}")
            return True, tts_duration

        logger.warning("Qwen-TTS generation failed (empty file)")
    except TimeoutError:
        logger.error(f"[TTS] Generation timed out ({TTS_TIMEOUT_SECONDS}s) for scene {i}")
    except Exception as e:
        logger.error(f"TTS generation error (Qwen): {e}")

    return False, 0.0
