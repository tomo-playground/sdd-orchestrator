"""Voice design resolution for TTS pipeline.

Contains Gemini-based voice prompt generation and the 4-priority
voice design resolution logic, extracted from tts_helpers.py.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import MutableMapping

from config import (
    DEFAULT_SPEAKER,
    GEMINI_TEXT_MODEL,
    gemini_client,
    logger,
)

_CACHE_MAXSIZE = 256


# ── LRU Cache (module-local to avoid circular imports with tts_helpers) ──


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
                "You are an expert voice director. Your task is to MINIMALLY ADJUST the provided 'Base Voice Description' "
                "to match the emotional 'Scene Context' and 'Script'.\n"
                "STRICT RULES:\n"
                "1. Keep the speaker's age, gender, vocal quality, and fundamental voice characteristics IDENTICAL to the Base Description.\n"
                "2. Only adjust ONE emotional modifier (tone/feeling). Do NOT rewrite the base description.\n"
                "3. The output must sound like the SAME PERSON as the base voice, just with slightly different emotion.\n"
                "4. Prefer subtle adjustments: 'calm' → 'slightly warm', NOT 'calm' → 'desperately crying'.\n"
                "5. FORBIDDEN: 'shouting', 'yelling', 'screaming', 'crying', 'desperate' unless the script is an extreme outburst.\n"
                "6. FORBIDDEN: changing the fundamental voice type (e.g. do NOT change 'deep male voice' to 'gentle soft voice').\n"
                "Output ONLY the minimally modified English description.\n"
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
                "You are an expert voice director. Generate a SHORT English voice description for a TTS engine.\n"
                "Rules:\n"
                "1. Describe the speaker's fundamental voice (age, gender, vocal quality) + ONE emotional tone.\n"
                "2. Prefer natural, conversational delivery. Avoid extremes.\n"
                "3. FORBIDDEN: 'shouting', 'yelling', 'screaming' unless the script explicitly demands it.\n"
                "4. The description should work for ALL scenes of this character (not too scene-specific).\n"
                "Output ONLY the English description. Keep it under 15 words."
            )
            user_prompt_content = (
                f"Script (Korean): {script}\nScene Context: {context_text}\n\nVoice Design Prompt (English):"
            )

        from google.genai.types import GenerateContentConfig

        from config import GEMINI_SAFETY_SETTINGS

        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=user_prompt_content,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                safety_settings=GEMINI_SAFETY_SETTINGS,
            ),
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


def resolve_voice_design(
    *,
    scene_voice_design: str | None,
    preset_voice_design: str | None,
    global_voice_design: str | None,
    scene_emotion: str | None,
    clean_script: str,
    image_prompt_ko: str | None = None,
    speaker: str | None = None,
    scene_idx: int = 0,
) -> tuple[str | None, bool]:
    """4-Priority voice design resolution.

    Returns: (voice_design, was_gemini_generated)

    Priority 0: scene_voice_design (pipeline result reuse)
    Priority 1: preset + Gemini emotion adaptation (skip Gemini in consistency mode)
    Priority 2: explicit per-scene/global prompt
    Priority 3: Gemini context-aware auto-generation
    """
    from config import TTS_VOICE_CONSISTENCY_MODE

    _speaker = speaker or DEFAULT_SPEAKER

    # Priority 0: pipeline-generated prompt (TTS Designer -> Finalize -> DB)
    if scene_voice_design:
        logger.info("Scene %d: Voice design (Speaker=%s): Priority 0 — pipeline prompt", scene_idx, _speaker)
        return scene_voice_design, False

    # Priority 1: preset + Gemini emotion adaptation
    if preset_voice_design:
        if TTS_VOICE_CONSISTENCY_MODE:
            logger.info(
                "Scene %d: Voice design (Speaker=%s): Priority 1 — consistency mode (preset only)",
                scene_idx,
                _speaker,
            )
            return preset_voice_design, False

        context_parts: list[str] = []
        if scene_emotion:
            context_parts.append(f"Emotion: {scene_emotion}")
        if image_prompt_ko:
            context_parts.append(image_prompt_ko)

        context_text = ". ".join(context_parts)
        if context_text:
            adapted = generate_context_aware_voice_prompt(clean_script, context_text, base_prompt=preset_voice_design)
            if adapted:
                logger.info(
                    "Scene %d: Voice design (Speaker=%s): Priority 1 — Gemini-adapted from preset",
                    scene_idx,
                    _speaker,
                )
                return adapted, True

        # Fallback: simple concatenation
        if scene_emotion:
            result = f"{preset_voice_design}, {scene_emotion}"
            logger.info("Scene %d: Voice design (Speaker=%s): Priority 1 — base + emotion", scene_idx, _speaker)
        else:
            result = preset_voice_design
            logger.info("Scene %d: Voice design (Speaker=%s): Priority 1 — base preset only", scene_idx, _speaker)
        return result, False

    # Priority 2: explicit per-scene or global prompt
    voice_design = scene_voice_design or global_voice_design
    if voice_design:
        logger.info("Scene %d: Voice design (Speaker=%s): Priority 2 — explicit prompt", scene_idx, _speaker)
        return voice_design, False

    # Priority 3: Gemini context-aware generation
    context_parts_3: list[str] = []
    if scene_emotion:
        context_parts_3.append(f"Emotion: {scene_emotion}")
    if image_prompt_ko:
        context_parts_3.append(image_prompt_ko)

    context_text_3 = ". ".join(context_parts_3)
    if context_text_3:
        auto = generate_context_aware_voice_prompt(clean_script, context_text_3)
        if auto:
            logger.info("Scene %d: Voice design (Speaker=%s): Priority 3 — Gemini auto-generated", scene_idx, _speaker)
            return auto, True

    return None, False
