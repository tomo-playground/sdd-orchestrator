"""Scene processing for the video pipeline.

Handles per-scene image loading, TTS generation, subtitle text wrapping,
and post-layout image composition. Each function receives the VideoBuilder
instance as its first argument.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

import torch
from qwen_tts import Qwen3TTSModel

from config import (
    GEMINI_TEXT_MODEL,
    STORAGE_MODE,
    TTS_ATTN_IMPLEMENTATION,
    TTS_BASE_MODEL_NAME,
    TTS_DEFAULT_LANGUAGE,
    TTS_DEVICE,
    TTS_MODEL_NAME,
    gemini_client,
    logger,
)
from services.storage import get_storage
from services.video.utils import clean_script_for_tts

# Global model cache for Qwen-TTS (single model swap)
_current_model = None
_current_model_type: str | None = None
_model_lock = asyncio.Lock()

# Simple cache: Korean prompt → English translation
_VOICE_PROMPT_CACHE: dict[str, str] = {}
_HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def _resolve_device() -> str:
    device = TTS_DEVICE
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    return device


def _load_model(model_name: str):
    """Load a Qwen-TTS model (blocking)."""
    device = _resolve_device()
    logger.info(f"Loading Qwen-TTS model ({model_name}) on {device}...")
    model = Qwen3TTSModel.from_pretrained(
        model_name,
        dtype=torch.bfloat16 if device == "mps" else torch.float32,
        attn_implementation=TTS_ATTN_IMPLEMENTATION,
    )
    model.model.to(device)
    model.device = torch.device(device)
    return model


def get_qwen_model():
    """Synchronous model getter (for lifespan preload). Loads VoiceDesign model."""
    global _current_model, _current_model_type
    if _current_model is None:
        _current_model = _load_model(TTS_MODEL_NAME)
        _current_model_type = "voice_design"
    return _current_model


async def get_qwen_model_async(model_type: str = "voice_design"):
    """Async model getter with single-model swap.

    Only one model is loaded at a time. If a different model type is requested,
    the current model is unloaded first to conserve memory.
    """
    global _current_model, _current_model_type
    async with _model_lock:
        if _current_model_type == model_type and _current_model is not None:
            return _current_model
        # Unload previous model
        if _current_model is not None:
            logger.info(f"[TTS] Swapping model: {_current_model_type} → {model_type}")
            del _current_model
            _current_model = None
            _current_model_type = None
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
        # Load new model in executor to avoid blocking
        model_name = TTS_MODEL_NAME if model_type == "voice_design" else TTS_BASE_MODEL_NAME
        loop = asyncio.get_event_loop()
        _current_model = await loop.run_in_executor(None, _load_model, model_name)
        _current_model_type = model_type
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
    for i, scene in enumerate(builder.request.scenes):
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
            builder, i, clean_script, tts_path
        )

        # Add to input args
        builder.input_args.extend(["-loop", "1", "-i", str(img_path)])
        if has_valid_tts:
            builder.input_args.extend(["-i", str(tts_path)])
        else:
            builder.input_args.extend([
                "-f", "lavfi", "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
            ])

        builder.tts_valid.append(has_valid_tts)
        builder.tts_durations.append(tts_duration)


def _load_scene_image(builder: VideoBuilder, img_src: str | None) -> bytes:
    """Load scene image bytes from storage or URL fallback."""
    if img_src and (
        "/projects/" in img_src
        or (STORAGE_MODE == "s3" and "shorts-producer" in img_src)
    ):
        try:
            if "projects/" in img_src:
                storage_key = "projects/" + img_src.split("projects/", 1)[1]
                storage = get_storage()
                local_path = storage.get_local_path(storage_key)
                image_bytes = local_path.read_bytes()
                logger.info(
                    "[Video Build] Loaded image from storage: %s", storage_key
                )
                return image_bytes
            return builder._load_image_bytes(img_src)
        except Exception as e:
            logger.warning(
                "[Video Build] Failed to load from storage, fallback to URL: %s", e
            )
            return builder._load_image_bytes(img_src)
    return builder._load_image_bytes(img_src)


def wrap_scene_text(
    builder: VideoBuilder, text: str
) -> tuple[list[str], int]:
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
            all_fit = all(
                not (bbox := font.getbbox(line)) or (bbox[2] - bbox[0]) <= max_width_px
                for line in lines
            )
            if all_fit:
                if font_size < base_font_size:
                    logger.info(
                        f"Dynamic font: {base_font_size}px -> {font_size}px "
                        f"for text: {text[:30]}..."
                    )
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
    builder: VideoBuilder, i: int, image_bytes: bytes, img_path: Path
) -> None:
    """Process image for post layout."""
    try:
        overlay_settings = (
            builder.request.overlay_settings or builder._OverlaySettings()
        )
        post_settings = (
            builder.request.post_card_settings
            or builder._PostCardSettings(
                channel_name=overlay_settings.channel_name,
                avatar_key=overlay_settings.avatar_key,
                caption=overlay_settings.caption,
            )
        )
        subtitle_text = (
            "\n".join(builder.subtitle_lines[i])
            if builder.subtitle_lines[i]
            else ""
        )
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


def _get_preset_voice_design(voice_preset_id: int) -> str | None:
    """Fetch voice_design_prompt from a voice preset for VoiceDesign fallback."""
    from database import get_db
    from models.voice_preset import VoicePreset

    db = next(get_db())
    try:
        preset = db.get(VoicePreset, voice_preset_id)
        if preset and preset.voice_design_prompt:
            logger.info(f"[TTS] Preset {voice_preset_id} voice_design_prompt: {preset.voice_design_prompt[:40]}")
            return preset.voice_design_prompt
        return None
    except Exception as e:
        logger.error(f"[TTS] Failed to get preset voice design: {e}")
        return None
    finally:
        db.close()


def _get_preset_audio_info(voice_preset_id: int) -> tuple[Path | None, str | None]:
    """Fetch voice preset audio path and sample_text (ref_text) from DB."""
    from database import get_db
    from models.media_asset import MediaAsset
    from models.voice_preset import VoicePreset

    db = next(get_db())
    try:
        preset = db.get(VoicePreset, voice_preset_id)
        if not preset or not preset.audio_asset_id:
            return None, None
        asset = db.get(MediaAsset, preset.audio_asset_id)
        if not asset:
            return None, None
        local = Path(asset.local_path)
        if local.exists():
            return local, preset.sample_text
        return None, None
    except Exception as e:
        logger.error(f"[TTS] Failed to get preset audio path: {e}")
        return None, None
    finally:
        db.close()


async def _generate_tts_with_preset(
    raw_script: str, voice_preset_id: int, tts_path: Path, language: str,
) -> bool:
    """Generate TTS using Base model + voice preset audio for cloning."""
    ref_path, ref_text = _get_preset_audio_info(voice_preset_id)
    if not ref_path:
        logger.warning(f"[TTS] Preset {voice_preset_id} audio not found, falling back to VoiceDesign")
        return False

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            model = await get_qwen_model_async("base")
            loop = asyncio.get_event_loop()

            def _clone():
                import soundfile as sf
                wavs, sr = model.generate_voice_clone(
                    text=raw_script,
                    ref_audio=str(ref_path),
                    ref_text=ref_text or "",
                    language=language,
                )
                sf.write(str(tts_path), wavs[0], sr)

            await loop.run_in_executor(None, _clone)

            if tts_path.exists() and tts_path.stat().st_size > 0:
                return True
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"[TTS] Clone attempt {attempt + 1} failed, retrying: {e}")
            else:
                logger.error(f"[TTS] Clone failed after {max_retries + 1} attempts: {e}")
    return False


async def generate_tts(
    builder: VideoBuilder, i: int, raw_script: str, tts_path: Path
) -> tuple[bool, float]:
    """Generate TTS audio for a scene (Qwen-TTS only).

    If voice_preset_id is set, uses Base model + cloning.
    Otherwise, uses VoiceDesign model (existing behavior).
    """
    if not raw_script.strip():
        logger.warning(f"Scene {i}: empty script, skipping TTS")
        return False, 0.0

    scene_req = builder.request.scenes[i]
    preset_voice_design: str | None = None

    try:
        # Voice Preset mode: Base model + cloning
        if builder.request.voice_preset_id:
            logger.info(f"TTS generation (Clone): preset={builder.request.voice_preset_id}, script={raw_script[:50]}...")
            # Fetch preset's voice_design_prompt for fallback
            preset_voice_design = _get_preset_voice_design(builder.request.voice_preset_id)
            success = await _generate_tts_with_preset(
                raw_script, builder.request.voice_preset_id, tts_path, TTS_DEFAULT_LANGUAGE,
            )
            if success:
                tts_duration = builder._get_audio_duration(tts_path)
                logger.info(f"TTS success (Clone): duration={tts_duration}s")
                return True, tts_duration
            # Fallback to VoiceDesign
            logger.warning("[TTS] Clone failed, falling back to VoiceDesign")

        # VoiceDesign mode (default or fallback from preset)
        logger.info(f"TTS generation (VoiceDesign): script={raw_script[:50]}...")
        model = await get_qwen_model_async("voice_design")

        voice_design = (
            scene_req.voice_design_prompt
            or preset_voice_design
            or builder.request.voice_design_prompt
        )
        voice_design = _translate_voice_prompt(voice_design or "")

        import soundfile as sf

        loop = asyncio.get_event_loop()

        def _voice_design():
            return model.generate_voice_design(
                text=raw_script,
                instruct=voice_design or "",
                language=TTS_DEFAULT_LANGUAGE,
            )

        logger.info(f"Scene {i}: voice design — '{(voice_design or '')[:40]}'")
        wavs, sr = await loop.run_in_executor(None, _voice_design)

        sf.write(str(tts_path), wavs[0], sr)

        if tts_path.exists() and tts_path.stat().st_size > 0:
            tts_duration = builder._get_audio_duration(tts_path)
            logger.info(f"TTS success (VoiceDesign): duration={tts_duration}s")
            return True, tts_duration

        logger.warning("Qwen-TTS generation failed (empty file)")
    except Exception as e:
        logger.error(f"TTS generation error (Qwen): {e}")

    return False, 0.0
