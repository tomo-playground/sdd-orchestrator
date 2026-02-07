"""TTS helper functions for Qwen3-TTS model management.

Handles model loading, voice preset resolution, voice prompt translation,
and caching. Extracted from scene_processing.py for modularity.
"""

from __future__ import annotations

import asyncio
import hashlib
import re

import torch as _torch
from qwen_tts import Qwen3TTSModel as _Qwen3TTSModel

from config import (
    DEFAULT_SPEAKER,
    GEMINI_TEXT_MODEL,
    TTS_ATTN_IMPLEMENTATION,
    TTS_DEVICE,
    TTS_MODEL_NAME,
    gemini_client,
    logger,
)

_TTS_AVAILABLE = True

# Global model cache for Qwen-TTS (single model swap)
_current_model = None
_current_model_type: str | None = None
_model_lock = asyncio.Lock()

# Simple cache: Korean prompt -> English translation
_VOICE_PROMPT_CACHE: dict[str, str] = {}
_HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def _ensure_tts_deps() -> bool:
    """Check TTS availability. Always returns True with eager loading."""
    return _TTS_AVAILABLE


def tts_cache_key(
    text: str,
    voice_preset_id: int | None,
    voice_design_prompt: str | None,
    language: str,
) -> str:
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
    """Synchronous model getter (for lifespan preload).

    Always loads VoiceDesign model.
    """
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


def translate_voice_prompt(prompt: str) -> str:
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
        logger.info(f"[TTS] Voice prompt translated: '{prompt}' -> '{translated}'")
        return translated
    except Exception as e:
        logger.warning(f"[TTS] Voice prompt translation failed: {e}")
        return prompt


def get_preset_voice_info(
    voice_preset_id: int,
) -> tuple[str | None, int | None]:
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


def get_speaker_voice_preset(storyboard_id: int | None, speaker: str) -> int | None:
    """Resolve speaker to a voice_preset_id from Storyboard/Character.

    - "Narrator" -> Storyboard.narrator_voice_preset_id
    - Character name (e.g. "A") -> Character.voice_preset_id
      looked up via character_id on the storyboard.
    """
    if not storyboard_id:
        logger.debug("[TTS] get_speaker_voice_preset: no storyboard_id, returning None")
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

        # Non-narrator speaker -> resolve via storyboard_characters
        from services.speaker_resolver import resolve_speaker_to_character

        resolved_char_id = resolve_speaker_to_character(storyboard_id, speaker, db)
        if not resolved_char_id:
            logger.warning(
                f"[TTS] No character mapping for speaker '{speaker}' "
                f"in storyboard {storyboard_id}. "
                f"Falling back to default voice."
            )
            return None
        char = db.get(Character, resolved_char_id)
        if char and char.voice_preset_id:
            logger.info(
                f"[TTS] Speaker '{speaker}' voice preset from "
                f"character {char.name}({resolved_char_id}): "
                f"{char.voice_preset_id}"
            )
            return char.voice_preset_id
        return None
    except Exception as e:
        logger.error(f"[TTS] Failed to resolve speaker voice preset: {e}")
        return None
    finally:
        db.close()
