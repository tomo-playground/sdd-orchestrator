"""TTS helper functions: voice preset resolution, voice prompt translation, caching.

Model loading has been moved to Audio Server sidecar.
This module retains DB/business logic only.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import os
import re
import shutil
import tempfile
import wave
from collections import OrderedDict
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path

from config import (
    DEFAULT_SPEAKER,
    GEMINI_TEXT_MODEL,
    TTS_CACHE_DIR,
    gemini_client,
    logger,
)
from services.video.tts_voice_design import (  # noqa: F401 — re-export for backward compat
    generate_context_aware_voice_prompt,
    resolve_voice_design,
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
    scene_emotion: str = "",
    speaker: str | None = None,
) -> str:
    """Deterministic hash for TTS caching based on text + voice config.

    Includes TTS_NATURALNESS_SUFFIX so cache auto-invalidates when
    the global suffix setting changes. speaker를 포함하여 화자별 캐시 분리.

    Note: Phase 30-O에서 speaker 파라미터 추가로 기존 캐시 키 형식 변경됨.
    배포 시 기존 TTS 캐시가 자연스럽게 miss 처리되어 재생성됨 (의도된 동작).
    """
    from config import TTS_NATURALNESS_SUFFIX

    parts = (
        f"{text}|{voice_preset_id}|{voice_design_prompt or ''}|"
        f"{language}|{scene_emotion or ''}|{speaker or ''}|{TTS_NATURALNESS_SUFFIX}"
    )
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
        from google.genai.types import GenerateContentConfig

        from config import GEMINI_SAFETY_SETTINGS

        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=(
                    "Translate the following Korean TTS voice description to English. "
                    "Return ONLY the translated text, nothing else."
                ),
                safety_settings=GEMINI_SAFETY_SETTINGS,
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
            "🔊 [TTS] Speaker '%s' could not be resolved to a character (storyboard_id=%d). Falling back to default voice.",
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


# ── Shared concurrency semaphore (preview + prebuild 공용) ──────────────
from config import TTS_PREBUILD_CONCURRENCY  # noqa: E402

TTS_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(TTS_PREBUILD_CONCURRENCY)


@dataclass
class TtsAudioResult:
    """TTS 생성 결과 (DB/저장 무관한 순수 오디오 + 메타데이터)."""

    audio_bytes: bytes
    duration: float
    cache_key: str
    cached: bool
    voice_seed: int
    voice_design: str | None
    was_gemini_generated: bool  # Gemini가 새로 생성했는지 (write-back 판단용)


def _wav_duration(wav_bytes: bytes) -> float:
    """WAV 바이트에서 재생 시간(초)을 계산한다."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate if rate > 0 else 0.0


def _calculate_max_new_tokens(text: str) -> int:
    """텍스트 길이 기반 동적 max_new_tokens. Qwen3-TTS 12Hz 기준 안전 마진."""
    from config import TTS_MAX_NEW_TOKENS_BASE, TTS_MAX_NEW_TOKENS_CAP, TTS_MAX_NEW_TOKENS_PER_CHAR

    dynamic = len(text) * TTS_MAX_NEW_TOKENS_PER_CHAR
    return min(max(dynamic, TTS_MAX_NEW_TOKENS_BASE), TTS_MAX_NEW_TOKENS_CAP)


def _atomic_cache_write(src: Path, dst: Path) -> None:
    """src를 dst로 원자적으로 복사 (같은 파일시스템 rename)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dst.parent, suffix=".tmp")
    try:
        os.close(tmp_fd)
        shutil.copy2(src, tmp_path)
        os.replace(tmp_path, dst)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def persist_voice_design(scene_idx: int, scene_db_id: int | None, voice_design: str) -> None:
    """Gemini 생성 voice design을 DB에 write-back (non-fatal).

    이후 렌더에서 Priority 0으로 재사용되어 일관된 음성을 보장한다.
    scene_db_id가 없으면 no-op.
    """
    if not scene_db_id:
        return
    try:
        from database import get_db_session  # noqa: PLC0415
        from models import Scene as SceneModel  # noqa: PLC0415

        with get_db_session() as _db:
            _db.query(SceneModel).filter(
                SceneModel.id == scene_db_id,
                SceneModel.deleted_at.is_(None),
            ).update({"voice_design_prompt": voice_design})
            _db.commit()
        logger.info("Scene %d (db_id=%d): voice_design_prompt write-back 완료", scene_idx, scene_db_id)
    except Exception as _e:
        logger.warning("Scene %d: voice_design_prompt write-back 실패 (non-fatal): %s", scene_idx, _e)


@dataclass
class _ResolvedTtsParams:
    """generate_tts_audio 내부에서 사용하는 해석 완료 파라미터 묶음."""

    tts_text: str
    cleaned: str
    language: str
    voice_seed: int
    cache_key: str
    cache_path: Path
    preset_voice_design: str | None
    voice_design_final: str
    was_gemini: bool
    min_duration: float
    retries: int


def _resolve_voice_seed(
    preset_seed: int | None,
    preset_voice_design: str | None,
    default_seed: int,
) -> int:
    """Seed 우선순위: preset seed > prompt hash > fixed default."""
    if preset_seed:
        return preset_seed
    if preset_voice_design:
        return int(hashlib.sha256(preset_voice_design.encode()).hexdigest()[:8], 16) % (2**31)
    return default_seed


def _calculate_min_duration(cleaned: str, default_min: float) -> float:
    """발화 가능 문자 길이에 따른 최소 TTS duration 결정."""
    speakable_len = len(cleaned.replace(".", "").replace("!", "").replace("?", "").strip())
    if speakable_len <= 3:
        return 0.4
    if speakable_len <= 6:
        return 0.6
    return default_min


def _resolve_tts_params(
    *,
    script: str,
    speaker: str,
    voice_preset_id: int | None,
    scene_voice_design: str | None,
    global_voice_design: str | None,
    scene_emotion: str,
    language: str | None,
    force_regenerate: bool,
    max_retries: int,
    image_prompt_ko: str | None,
) -> tuple[_ResolvedTtsParams | None, TtsAudioResult | None]:
    """스크립트 전처리, 프리셋/시드/캐시/보이스 디자인 해석.

    캐시 히트 시 Gemini 호출을 건너뛰고 즉시 결과를 반환한다.
    Returns: (params, cache_hit) -- cache_hit이 not None이면 즉시 반환 가능.
    """
    from config import TTS_DEFAULT_LANGUAGE, TTS_DEFAULT_SEED, TTS_MAX_RETRIES, TTS_MIN_DURATION_SEC
    from services.video.utils import clean_script_for_tts, has_speakable_content  # noqa: PLC0415

    _language = language or TTS_DEFAULT_LANGUAGE
    cleaned = clean_script_for_tts(script.strip())
    if not cleaned or not has_speakable_content(cleaned):
        raise ValueError("스크립트에 TTS로 변환할 내용이 없습니다.")
    tts_text = cleaned if len(cleaned.strip()) >= 3 else cleaned.strip() + "."

    preset_voice_design, preset_seed = get_preset_voice_info(voice_preset_id) if voice_preset_id else (None, None)
    voice_seed = _resolve_voice_seed(preset_seed, preset_voice_design, TTS_DEFAULT_SEED)
    cache_key = tts_cache_key(
        cleaned,
        voice_preset_id,
        scene_voice_design or global_voice_design,
        _language,
        scene_emotion,
        speaker=speaker,
    )
    cache_path = TTS_CACHE_DIR / f"{cache_key}.wav"

    if force_regenerate and cache_path.exists():
        cache_path.unlink()
        logger.info("[TTS] force_regenerate: cache deleted (%s)", cache_key)

    # Cache hit -- skip Gemini voice design resolution
    cache_hit = _check_cache_hit(
        cache_path,
        cache_key,
        voice_seed,
        scene_voice_design,
        global_voice_design,
        preset_voice_design,
    )
    if cache_hit:
        return None, cache_hit

    # Voice design resolution (may invoke Gemini -- only on cache miss)
    resolved_vd, was_gemini = resolve_voice_design(
        scene_voice_design=scene_voice_design,
        preset_voice_design=preset_voice_design,
        global_voice_design=global_voice_design,
        scene_emotion=scene_emotion,
        clean_script=cleaned,
        image_prompt_ko=image_prompt_ko,
        speaker=speaker,
    )
    return _ResolvedTtsParams(
        tts_text=tts_text,
        cleaned=cleaned,
        language=_language,
        voice_seed=voice_seed,
        cache_key=cache_key,
        cache_path=cache_path,
        preset_voice_design=preset_voice_design,
        voice_design_final=translate_voice_prompt(resolved_vd or ""),
        was_gemini=was_gemini,
        min_duration=_calculate_min_duration(cleaned, TTS_MIN_DURATION_SEC),
        retries=max_retries if max_retries >= 0 else TTS_MAX_RETRIES,
    ), None


def _check_cache_hit(
    cache_path: Path,
    cache_key: str,
    voice_seed: int,
    scene_voice_design: str | None,
    global_voice_design: str | None,
    preset_voice_design: str | None,
) -> TtsAudioResult | None:
    """캐시 파일이 유효하면 TtsAudioResult를 반환, 없으면 None."""
    if not cache_path.exists() or cache_path.stat().st_size == 0:
        return None
    audio_bytes = cache_path.read_bytes()
    duration = _wav_duration(audio_bytes)
    logger.info("[TTS] Cache hit: %s (%.1fs)", cache_key, duration)
    vd_meta = scene_voice_design or global_voice_design or preset_voice_design
    return TtsAudioResult(
        audio_bytes=audio_bytes,
        duration=duration,
        cache_key=cache_key,
        cached=True,
        voice_seed=voice_seed,
        voice_design=vd_meta,
        was_gemini_generated=False,
    )


async def _try_synthesize_with_retries(
    p: _ResolvedTtsParams,
    *,
    task_id: str,
    force: bool = False,
) -> TtsAudioResult:
    """리트라이 루프: 합성 → 품질 확인 → 캐시 기록 → best fallback."""
    from config import TTS_REPETITION_PENALTY, TTS_TEMPERATURE, TTS_TOP_P
    from services.audio_client import synthesize_tts  # noqa: PLC0415

    best_bytes: bytes | None = None
    best_dur = 0.0

    for attempt in range(1 + p.retries):
        attempt_seed = p.voice_seed + attempt * 7919
        current_vd = _simplify_voice_design(attempt, p.voice_design_final, p.preset_voice_design)

        try:
            audio_bytes, _sr, duration, quality_passed = await synthesize_tts(
                text=p.tts_text,
                instruct=current_vd or "",
                language=p.language,
                seed=attempt_seed,
                temperature=TTS_TEMPERATURE,
                top_p=TTS_TOP_P,
                repetition_penalty=TTS_REPETITION_PENALTY,
                max_new_tokens=_calculate_max_new_tokens(p.tts_text),
                task_id=task_id,
                force=force and attempt == 0,
            )
        except Exception as gen_err:
            logger.warning("[TTS] attempt %d/%d audio server error: %s", attempt + 1, 1 + p.retries, gen_err)
            continue

        if duration > best_dur:
            best_bytes, best_dur = audio_bytes, duration

        if quality_passed and duration >= p.min_duration:
            _write_cache(audio_bytes, p.cache_path)
            final_dur = _wav_duration(audio_bytes)
            if attempt > 0:
                logger.info("[TTS] Passed on attempt %d, duration=%.2fs", attempt + 1, final_dur)
            else:
                logger.info("[TTS] Generated: duration=%.2fs, seed=%d", final_dur, attempt_seed)
            return TtsAudioResult(
                audio_bytes=audio_bytes,
                duration=final_dur,
                cache_key=p.cache_key,
                cached=False,
                voice_seed=attempt_seed,
                voice_design=p.voice_design_final,
                was_gemini_generated=p.was_gemini,
            )

        logger.warning("[TTS] attempt %d/%d failed quality/duration (%.2fs)", attempt + 1, 1 + p.retries, duration)

    # Best fallback
    if best_bytes is not None and best_dur > 0:
        final_dur = _wav_duration(best_bytes)
        logger.warning("[TTS] All retries exhausted, using best attempt (%.2fs, uncached)", best_dur)
        return TtsAudioResult(
            audio_bytes=best_bytes,
            duration=final_dur,
            cache_key=p.cache_key,
            cached=False,
            voice_seed=p.voice_seed,
            voice_design=p.voice_design_final,
            was_gemini_generated=p.was_gemini,
        )

    raise RuntimeError(f"TTS 생성 실패 (모든 {1 + p.retries}회 시도 실패): script='{p.cleaned[:30]}'")


def _simplify_voice_design(
    attempt: int,
    voice_design_final: str,
    preset_voice_design: str | None,
) -> str:
    """리트라이 차수에 따라 voice design을 점진적으로 단순화."""
    if attempt == 0:
        return voice_design_final
    if attempt == 1 and voice_design_final:
        simplified = ", ".join(voice_design_final.split(",")[:1]).strip()
        logger.info("[TTS] Attempt 2: simplified voice design")
        return simplified
    # attempt >= 2
    minimal = translate_voice_prompt(preset_voice_design or "")
    logger.info("[TTS] Attempt 3+: minimal voice design (preset only)")
    return minimal


def _write_cache(audio_bytes: bytes, cache_path: Path) -> None:
    """합성 결과를 캐시 파일에 원자적으로 기록."""
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path_str = tempfile.mkstemp(dir=TTS_CACHE_DIR, suffix=".wav")
    try:
        os.close(tmp_fd)
        Path(tmp_path_str).write_bytes(audio_bytes)
        _atomic_cache_write(Path(tmp_path_str), cache_path)
    finally:
        if os.path.exists(tmp_path_str):
            os.unlink(tmp_path_str)


async def generate_tts_audio(
    *,
    script: str,
    speaker: str = DEFAULT_SPEAKER,
    voice_preset_id: int | None = None,
    scene_voice_design: str | None = None,
    global_voice_design: str | None = None,
    scene_emotion: str = "",
    language: str | None = None,
    force_regenerate: bool = False,
    max_retries: int = 0,
    image_prompt_ko: str | None = None,
    scene_db_id: int | None = None,
    task_id: str = "default",
) -> TtsAudioResult:
    """TTS 오디오 생성 코어 함수 (SSOT).

    Qwen3-TTS를 유일 엔진으로 사용한다.
    모든 TTS 생성은 이 함수를 통한다.
    DB 저장/MinIO 업로드는 호출측(preview_tts, tts_prebuild) 책임.
    """
    params, cache_hit = _resolve_tts_params(
        script=script,
        speaker=speaker,
        voice_preset_id=voice_preset_id,
        scene_voice_design=scene_voice_design,
        global_voice_design=global_voice_design,
        scene_emotion=scene_emotion,
        language=language,
        force_regenerate=force_regenerate,
        max_retries=max_retries,
        image_prompt_ko=image_prompt_ko,
    )
    if cache_hit:
        return cache_hit

    assert params is not None  # guaranteed when cache_hit is None
    return await _try_synthesize_with_retries(params, task_id=task_id, force=force_regenerate)
