"""TTS Designer 노드 — 씬별 음성 디자인(감정, 톤, 페이싱)을 생성한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.state import ScriptState
from services.creative_qc import validate_tts_design

_FALLBACK_TTS = {"tts_designs": []}


def _load_character_voice_context(state: ScriptState) -> list[dict] | None:
    """캐릭터 ID로 성별/이름/음성 프리셋을 로드하여 TTS Designer에 전달."""
    from database import get_db_session
    from models.character import Character
    from models.voice_preset import VoicePreset

    character_id = state.get("character_id")
    character_b_id = state.get("character_b_id")
    if not character_id:
        return None

    speakers: dict[str, int] = {"A": character_id}
    if character_b_id:
        speakers["B"] = character_b_id

    results: list[dict] = []
    with get_db_session() as db:
        for speaker, cid in speakers.items():
            char = db.query(Character).filter(Character.id == cid).first()
            if not char:
                continue
            info: dict = {
                "speaker": speaker,
                "name": char.name,
                "gender": char.gender or "female",
            }
            if char.voice_preset_id:
                preset = db.query(VoicePreset).filter(VoicePreset.id == char.voice_preset_id).first()
                if preset and preset.voice_design_prompt:
                    info["reference_voice"] = preset.voice_design_prompt
            results.append(info)

    return results if results else None


async def tts_designer_node(state: ScriptState) -> dict:
    """cinematographer_result의 씬을 기반으로 TTS 디자인을 생성한다."""
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "tts_designer"):
        return {"tts_designer_result": {"tts_designs": []}}

    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])
    concept = state.get("critic_result") or {}

    template_vars = {
        "scenes": scenes,
        "concept": concept,
        "language": state.get("language", "Korean"),
        "writer_plan": state.get("writer_plan"),
        "director_plan": state.get("director_plan"),
    }

    # 캐릭터 프로필 주입 (성별, 이름, 참조 음성)
    characters_voice = _load_character_voice_context(state)
    if characters_voice:
        template_vars["characters"] = characters_voice

    if director_feedback := state.get("director_feedback"):
        template_vars["feedback"] = director_feedback
    try:
        result = await run_production_step(
            template_name="creative/tts_designer.j2",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_tts_design(extracted),
            extract_key="tts_designs",
            step_name="tts_designer",
        )
        logger.info("[LangGraph] TTS Designer 완료: %d designs", len(result.get("tts_designs", [])))
        return {"tts_designer_result": result}
    except Exception as e:
        logger.warning("[LangGraph] TTS Designer 실패, fallback: %s", e)
        return {"tts_designer_result": _FALLBACK_TTS}
