"""TTS helper functions: voice preset resolution, voice prompt translation, caching.

Model loading has been moved to Audio Server sidecar.
This module retains DB/business logic only.
"""

from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from collections.abc import MutableMapping

from config import (
    DEFAULT_SPEAKER,
    GEMINI_TEXT_MODEL,
    gemini_client,
    logger,
)

_CACHE_MAXSIZE = 256


class _LRUCache(MutableMapping[str, str]):
    """Simple LRU cache with maxsize limit, dict-compatible interface."""

    def __init__(self, maxsize: int = 256) -> None:
        self._maxsize = maxsize
        self._data: OrderedDict[str, str] = OrderedDict()

    def __getitem__(self, key: str) -> str:
        self._data.move_to_end(key)
        return self._data[key]

    def __setitem__(self, key: str, value: str) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def pop(self, key: str, *args):
        return self._data.pop(key, *args)


# LRU caches: Korean prompt -> English translation (bounded)
_VOICE_PROMPT_CACHE: _LRUCache = _LRUCache(maxsize=_CACHE_MAXSIZE)
_HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def tts_cache_key(
    text: str,
    voice_preset_id: int | None,
    voice_design_prompt: str | None,
    language: str,
) -> str:
    """Deterministic hash for TTS caching based on text + voice config."""
    parts = f"{text}|{voice_preset_id}|{voice_design_prompt or ''}|{language}"
    return hashlib.sha256(parts.encode()).hexdigest()[:16]


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
        translated = (res.text or "").strip()
        _VOICE_PROMPT_CACHE[prompt] = translated
        logger.info("[TTS] Voice prompt translated: '%s' -> '%s'", prompt, translated)
        return translated
    except Exception as e:
        logger.warning("[TTS] Voice prompt translation failed: %s", e)
        return prompt


def get_preset_voice_info(
    voice_preset_id: int,
) -> tuple[str | None, int | None]:
    """Fetch voice_design_prompt and voice_seed from a voice preset."""
    from database import SessionLocal
    from models.voice_preset import VoicePreset

    db = SessionLocal()
    try:
        preset = db.get(VoicePreset, voice_preset_id)
        if not preset:
            return None, None
        prompt = preset.voice_design_prompt
        seed = preset.voice_seed
        if prompt:
            logger.info("[TTS] Preset %d: prompt='%s', seed=%s", voice_preset_id, prompt[:40], seed)
        return prompt, seed
    except Exception as e:
        logger.error("[TTS] Failed to get preset voice info: %s", e)
        return None, None
    finally:
        db.close()


def get_speaker_voice_preset(storyboard_id: int | None, speaker: str) -> int | None:
    """Resolve speaker to a voice_preset_id from Storyboard/Character."""
    if not storyboard_id:
        logger.debug("[TTS] get_speaker_voice_preset: no storyboard_id, returning None")
        return None

    from database import SessionLocal
    from models.group import Group
    from models.storyboard import Storyboard
    from services.config_resolver import resolve_effective_config

    db = SessionLocal()
    try:
        storyboard = db.get(Storyboard, storyboard_id)
        if not storyboard:
            return None

        group = db.get(Group, storyboard.group_id) if storyboard.group_id else None
        effective = resolve_effective_config(group.project, group) if group else {"values": {}}

        if speaker == DEFAULT_SPEAKER:
            return _resolve_narrator_preset(effective)
        return _resolve_character_preset(storyboard_id, speaker, db)
    except Exception as e:
        logger.error("[TTS] Failed to resolve speaker voice preset: %s", e)
        return None
    finally:
        db.close()


def _resolve_narrator_preset(effective: dict) -> int | None:
    """Extract narrator voice preset from effective config cascade."""
    preset_id = effective["values"].get("narrator_voice_preset_id")
    if preset_id:
        logger.info("[TTS] Narrator voice preset from cascade: %d", preset_id)
    return preset_id


def _resolve_character_preset(storyboard_id: int, speaker: str, db) -> int | None:
    """Resolve character speaker to a voice_preset_id via storyboard mapping."""
    from models.character import Character
    from services.characters import resolve_speaker_to_character

    resolved_char_id = resolve_speaker_to_character(storyboard_id, speaker, db)
    if not resolved_char_id:
        logger.warning(
            "[TTS] No character mapping for speaker '%s' in storyboard %d. Falling back to default voice.",
            speaker,
            storyboard_id,
        )
        return None
    char = db.get(Character, resolved_char_id)
    if char and char.voice_preset_id:
        logger.info(
            "[TTS] Speaker '%s' voice preset from character %s(%d): %d",
            speaker,
            char.name,
            resolved_char_id,
            char.voice_preset_id,
        )
        return char.voice_preset_id
    return None


# Cache: Context (script+prompt) -> Voice Design Prompt (English)
_CONTEXT_PROMPT_CACHE: _LRUCache = _LRUCache(maxsize=_CACHE_MAXSIZE)


def generate_context_aware_voice_prompt(
    script: str,
    context_text: str,
    base_prompt: str | None = None,
) -> str:
    """Generate a context-aware voice design prompt using Gemini."""
    if not gemini_client:
        return base_prompt or ""

    cache_key = f"{script[:50]}|{context_text[:100]}|{base_prompt or ''}"
    if cache_key in _CONTEXT_PROMPT_CACHE:
        return _CONTEXT_PROMPT_CACHE[cache_key]

    try:
        if base_prompt:
            system_instruction = (
                "You are an expert voice director. Your task is to MODIFY the provided 'Base Voice Description' "
                "to match the emotional 'Scene Context' and 'Script'.\n"
                "Keep the speaker's original age, gender, and core characteristics from the Base Description, "
                "but adjust the TONE and EMOTION to fit the scene. Prioritize natural, conversational delivery.\n"
                "IMPORTANT: For dialogue content, prefer subtle emotional expression over dramatic extremes. "
                "Avoid 'shouting', 'yelling', 'screaming' unless the script explicitly demands it.\n"
                "Output ONLY the modified English description (e.g., 'A calm female voice' -> 'A warm female voice with a gentle melancholic tone').\n"
                "Keep it under 20 words."
            )
            user_prompt_content = (
                f"Base Voice Description: {base_prompt}\n"
                f"Script (Korean): {script}\n"
                f"Scene Context: {context_text}\n\n"
                "Modified Voice Design Prompt (English):"
            )
        else:
            system_instruction = (
                "You are an expert voice director. Your task is to generate a SHORT, PRECISE "
                "English description of the speaker's voice and tone for a TTS engine.\n"
                "Analyze the provided Korean script and Scene Context (visuals/situation).\n"
                "IMPORTANT: Prefer natural, conversational tone. Avoid extreme expressions like "
                "'shouting', 'yelling', 'screaming' unless the script explicitly calls for it.\n"
                "Output ONLY the English description (e.g., 'A warm man speaking with mild frustration', 'A gentle woman whispering softly').\n"
                "Do NOT include the script itself. Keep it under 15 words."
            )
            user_prompt_content = (
                f"Script (Korean): {script}\nScene Context: {context_text}\n\nVoice Design Prompt (English):"
            )

        prompt = f"{system_instruction}\n\n{user_prompt_content}"

        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )

        voice_prompt = (res.text or "").strip()
        voice_prompt = voice_prompt.strip('"').strip("'")

        if voice_prompt:
            _CONTEXT_PROMPT_CACHE[cache_key] = voice_prompt
            logger.info("[TTS] Generated context prompt: '%s' (for '%s...')", voice_prompt, script[:20])
            return voice_prompt

    except Exception as e:
        logger.warning("[TTS] Failed to generate context-aware prompt: %s", e)

    return ""
