"""TTS 생성 통합 래퍼: 오토런/수동 경로 무관 동일 파라미터 보장.

이미지의 buildSceneRequest() 패턴에 대응하는 Backend 단일 진입점.
routes → tts_core(조립) → tts_helpers(엔진) 레이어 구조.

저장 정책(영구/임시)은 호출측(tts_prebuild, preview_tts)이 결정한다.
"""

from __future__ import annotations

from config import TTS_MAX_RETRIES, logger
from services.video.tts_helpers import (
    TtsAudioResult,
    generate_tts_audio,
    get_speaker_voice_preset,
    persist_voice_design,
)


async def generate_scene_tts(
    *,
    script: str,
    speaker: str,
    storyboard_id: int | None,
    scene_db_id: int | None = None,
    voice_design_prompt: str | None = None,
    scene_emotion: str | None = None,
    image_prompt_ko: str | None = None,
    language: str | None = None,
    force_regenerate: bool = False,
) -> TtsAudioResult:
    """TTS 생성 단일 진입점. 오토런/수동 모두 이 함수를 경유한다.

    - voice_preset_id resolve
    - generate_tts_audio 호출 (max_retries = config SSOT)
    - Gemini 생성 voice_design → DB write-back (scene_db_id가 있을 때)
    """
    voice_preset_id = get_speaker_voice_preset(storyboard_id, speaker)

    result: TtsAudioResult = await generate_tts_audio(
        script=script,
        speaker=speaker,
        voice_preset_id=voice_preset_id,
        scene_voice_design=voice_design_prompt,
        global_voice_design=None,
        scene_emotion=scene_emotion or "",
        language=language,
        force_regenerate=force_regenerate,
        max_retries=TTS_MAX_RETRIES,
        image_prompt_ko=image_prompt_ko,
        scene_db_id=scene_db_id,
    )

    if result.was_gemini_generated and result.voice_design and scene_db_id:
        persist_voice_design(scene_db_id, result.voice_design)
        logger.info("[TtsCore] Voice design write-back for scene %d", scene_db_id)

    return result
