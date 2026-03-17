"""Sound Designer 노드 — BGM 방향성을 추천한다."""

from __future__ import annotations

from config import logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.prompt_builders import (
    build_feedback_response_json_hint,
    build_feedback_section,
    build_language_hint,
    build_sound_emotional_arc_section,
    to_json,
)
from services.agent.state import ScriptState
from services.creative_qc import validate_music

_FALLBACK_SOUND = {
    "recommendation": {"prompt": "", "mood": "neutral", "duration": 30},
    "fallback_reason": "api_error",
}


async def sound_designer_node(state: ScriptState) -> dict:
    """cinematographer_result의 씬을 기반으로 BGM 추천을 생성한다."""
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "sound_designer"):
        return {"sound_designer_result": _FALLBACK_SOUND}

    cinema = state.get("cinematographer_result") or {}
    scenes = cinema.get("scenes", [])
    concept = state.get("critic_result") or {}
    duration = state.get("duration", 30)
    language = state.get("language", "Korean")

    feedback = state.get("director_feedback")
    template_vars = {
        "concept_json": to_json(concept),
        "scenes_json": to_json(scenes),
        "duration": str(duration),
        "language": language,
        "emotional_arc_section": build_sound_emotional_arc_section(state.get("writer_plan")),
        "feedback_section": build_feedback_section(feedback),
        "feedback_response_hint": build_feedback_response_json_hint(feedback),
        "language_hint": build_language_hint(language),
        "mood_progression": concept.get("mood_progression", ""),
    }
    try:
        result = await run_production_step(
            template_name="creative/sound_designer",
            template_vars=template_vars,
            validate_fn=lambda extracted: validate_music(extracted),
            extract_key="recommendation",
            step_name="generate_content sound_designer",
        )
        logger.info("[LangGraph] Sound Designer 완료")
        return {"sound_designer_result": result}
    except Exception as e:
        logger.warning("[LangGraph] Sound Designer 실패, fallback: %s", e)
        return {"sound_designer_result": _FALLBACK_SOUND}
