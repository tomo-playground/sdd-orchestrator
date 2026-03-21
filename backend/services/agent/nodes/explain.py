"""Explain 노드 — Full 모드에서 파이프라인의 창작 결정을 설명한다."""

from __future__ import annotations

from config import pipeline_logger as logger
from services.agent.nodes._production_utils import run_production_step
from services.agent.prompt_builders import (
    build_director_decision_section,
    build_feedback_section,
    build_scene_reasoning_section,
    to_json,
)
from services.agent.state import ScriptState


async def explain_node(state: ScriptState) -> dict:
    """Production 결과를 분석하여 창작 결정 설명을 생성한다."""
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "explain"):
        return {"explanation_result": None}

    logger.info("[LangGraph:Explain] 시작")
    template_vars = {
        "final_scenes_json": to_json(state.get("final_scenes") or []),
        "cinematographer_json": to_json(state.get("cinematographer_result") or {}),
        "tts_designer_json": to_json(state.get("tts_designer_result") or {}),
        "sound_designer_json": to_json(state.get("sound_designer_result") or {}),
        "copyright_reviewer_json": to_json(state.get("copyright_reviewer_result") or {}),
        "director_decision_section": build_director_decision_section(
            state.get("director_decision"),
            state.get("director_feedback"),
        ),
        "scene_reasoning_section": build_scene_reasoning_section(state.get("scene_reasoning") or []),
        "feedback_section": build_feedback_section(state.get("director_feedback")),
    }
    try:
        result = await run_production_step(
            template_name="creative/explain",
            template_vars=template_vars,
            validate_fn=lambda extracted: {"ok": bool(extracted), "issues": [], "checks": {}},
            extract_key="explanation",
            step_name="generate_content explain",
        )
        logger.info("[LangGraph] Explain 완료")
        return {"explanation_result": result}
    except Exception as e:
        logger.warning("[LangGraph] Explain 실패 (파이프라인 계속): %s", e)
        return {"explanation_result": None}
