"""TTS Designer 노드 — 씬별 음성 디자인(감정, 톤, 페이싱)을 생성한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.prompt_builders import (
    build_director_plan_section_for_tts,
    build_emotional_arc_section,
    build_feedback_response_json_hint,
    build_feedback_section,
    build_tts_characters_block,
    to_json,
)
from services.agent.state import ScriptState
from services.creative_qc import validate_tts_design

_FALLBACK_TTS = {"tts_designs": [], "fallback_reason": "api_error"}


def _load_character_voice_context(state: ScriptState) -> list[dict] | None:
    """캐릭터 ID + 그룹 Narrator 프리셋으로 음성 컨텍스트를 로드하여 TTS Designer에 전달."""
    from database import get_db_session
    from models.character import Character
    from models.group import Group
    from models.voice_preset import VoicePreset

    character_id = state.get("character_id")
    character_b_id = state.get("character_b_id")
    group_id = state.get("group_id")

    logger.info(
        "[TTS Voice] 음성 컨텍스트 로드 시작: character_id=%s, character_b_id=%s, group_id=%s",
        character_id,
        character_b_id,
        group_id,
    )

    if not character_id and not group_id:
        logger.info("[TTS Voice] 캐릭터/그룹 ID 없음 — 음성 컨텍스트 스킵")
        return None

    results: list[dict] = []
    speakers: dict[str, int] = {}
    if character_id:
        speakers["A"] = character_id
    if character_b_id:
        speakers["B"] = character_b_id

    with get_db_session() as db:
        for speaker, cid in speakers.items():
            char = db.query(Character).filter(Character.id == cid).first()
            if not char:
                logger.warning("[TTS Voice] Speaker %s: character_id=%s DB에 없음", speaker, cid)
                continue
            info: dict = {
                "speaker": speaker,
                "name": char.name,
                "gender": char.gender or "female",
                "has_preset": False,
            }
            if char.voice_preset_id:
                preset = db.query(VoicePreset).filter(VoicePreset.id == char.voice_preset_id).first()
                if preset and preset.voice_design_prompt:
                    info["reference_voice"] = preset.voice_design_prompt
                    info["has_preset"] = True
                    logger.info(
                        "[TTS Voice] Speaker %s(%s): Voice Preset 로드 (preset_id=%s)",
                        speaker,
                        char.name,
                        char.voice_preset_id,
                    )
                else:
                    logger.info(
                        "[TTS Voice] Speaker %s(%s): Voice Preset id=%s 존재하나 prompt 없음 → Gemini 생성",
                        speaker,
                        char.name,
                        char.voice_preset_id,
                    )
            else:
                logger.info(
                    "[TTS Voice] Speaker %s(%s): Voice Preset 미설정 → Gemini 생성",
                    speaker,
                    char.name,
                )
            results.append(info)

        # Narrator 보이스 — 그룹의 narrator_voice_preset 관계에서 로드 (추가 쿼리 없음)
        if group_id:
            group = db.query(Group).filter(Group.id == group_id).first()
            if group and group.narrator_voice_preset and group.narrator_voice_preset.voice_design_prompt:
                results.append(
                    {
                        "speaker": "Narrator",
                        "name": "Narrator",
                        "gender": "neutral",
                        "reference_voice": group.narrator_voice_preset.voice_design_prompt,
                        "has_preset": True,
                    }
                )
                logger.info("[TTS Voice] Narrator: Voice Preset 로드 (group_id=%s)", group_id)
            elif group:
                logger.info("[TTS Voice] Narrator: Voice Preset 미설정 (group_id=%s)", group_id)

    if results:
        preset_count = sum(1 for r in results if r.get("has_preset"))
        logger.info(
            "[TTS Voice] 음성 컨텍스트 로드 완료: %d명 (Preset: %d, Gemini 생성: %d)",
            len(results),
            preset_count,
            len(results) - preset_count,
        )
    else:
        logger.info("[TTS Voice] 음성 컨텍스트 없음 — 전체 Gemini 생성")

    return results if results else None


async def tts_designer_node(state: ScriptState) -> dict:
    """cinematographer_result의 씬을 기반으로 TTS 디자인을 생성한다."""
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "tts_designer"):
        return {"tts_designer_result": {"tts_designs": []}}

    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])
    concept = state.get("critic_result") or {}

    # 캐릭터 프로필 주입 (성별, 이름, 참조 음성)
    characters_voice = _load_character_voice_context(state)
    preset_speakers = {c["speaker"] for c in (characters_voice or []) if c.get("has_preset")}

    feedback = state.get("director_feedback")
    template_vars = {
        "concept_json": to_json(concept),
        "scenes_json": to_json(scenes),
        "director_plan_section": build_director_plan_section_for_tts(state.get("director_plan")),
        "emotional_arc_section": build_emotional_arc_section(state.get("writer_plan")),
        "characters_block": build_tts_characters_block(characters_voice),
        "feedback_section": build_feedback_section(feedback),
        "feedback_response_hint": build_feedback_response_json_hint(feedback),
    }
    try:
        result = await run_production_step(
            template_name="creative/tts_designer",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_tts_design(
                extracted if isinstance(extracted, list) else [],
                preset_speakers=preset_speakers,
            ),
            extract_key="tts_designs",
            step_name="generate_content tts_designer",
        )
        logger.info("[LangGraph] TTS Designer 완료: %d designs", len(result.get("tts_designs", [])))
        # QC 결과를 별도로 실행하여 Director 전달용 state에 저장
        qc = validate_tts_design(result.get("tts_designs", []), preset_speakers=preset_speakers)
        return {"tts_designer_result": result, "tts_qc_result": qc}
    except Exception as e:
        logger.warning("[LangGraph] TTS Designer 실패, fallback: %s", e)
        return {"tts_designer_result": _FALLBACK_TTS}
