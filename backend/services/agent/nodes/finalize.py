"""Finalize 노드 — Quick은 패스스루, Full은 Production 결과를 병합한다."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import DEFAULT_GAZE_TAG, DEFAULT_POSE_TAG, DEFAULT_SCENE_NEGATIVE_PROMPT, logger
from services.agent.state import ScriptState

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


def _inject_negative_prompts(scenes: list[dict]) -> None:
    """빈 negative_prompt에 기본값을 주입한다."""
    for scene in scenes:
        if not scene.get("negative_prompt"):
            scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT


def _merge_production_results(state: ScriptState) -> tuple[list[dict], dict | None, dict | None]:
    """cinematographer_result.scenes에 tts 결과를 병합하고, sound/copyright를 별도 반환."""
    cinema = state.get("cinematographer_result") or {}
    scenes = [dict(s) for s in cinema.get("scenes", [])]

    tts_designs = (state.get("tts_designer_result") or {}).get("tts_designs", [])
    sound_rec = (state.get("sound_designer_result") or {}).get("recommendation")
    copyright_result = state.get("copyright_reviewer_result")

    # TTS 디자인을 씬별로 병합
    for i, scene in enumerate(scenes):
        if i < len(tts_designs):
            scene["tts_design"] = tts_designs[i]

    logger.info("[LangGraph] Finalize (Full): %d scenes 병합 완료", len(scenes))
    return scenes, sound_rec, copyright_result


def _inject_default_context_tags(scenes: list[dict]) -> None:
    """캐릭터 씬의 context_tags에 pose/gaze 기본값을 주입한다.

    Gemini가 context_tags에 pose나 gaze를 누락하면 ControlNet에 데이터가
    전달되지 않으므로, 기본값을 채워서 character_actions 변환이 동작하도록 한다.
    Narrator 씬(배경샷)은 캐릭터가 없으므로 건너뛴다.
    """
    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker == "Narrator":
            continue

        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {"pose": DEFAULT_POSE_TAG, "gaze": DEFAULT_GAZE_TAG}
            continue

        if not ctx.get("pose"):
            ctx["pose"] = DEFAULT_POSE_TAG
        if not ctx.get("gaze"):
            ctx["gaze"] = DEFAULT_GAZE_TAG


async def finalize_node(state: ScriptState, config: RunnableConfig) -> dict:
    """Quick: draft → final 패스스루. Full: Production 결과 병합 + character_actions 변환."""
    # 에러 상태이면 즉시 반환 (에러 메시지 보존)
    if state.get("error"):
        logger.warning("[LangGraph] Finalize: 에러 상태 전파 → %s", state.get("error"))
        return {"error": state.get("error")}

    mode = state.get("mode", "quick")
    sound_rec: dict | None = None
    copyright_result: dict | None = None

    if mode == "full" and state.get("cinematographer_result"):
        scenes, sound_rec, copyright_result = _merge_production_results(state)
    else:
        scenes = [dict(s) for s in (state.get("draft_scenes") or [])]

    _inject_negative_prompts(scenes)
    _inject_default_context_tags(scenes)

    # character_actions 변환: context_tags → ControlNet 포즈/표정 데이터
    character_id = state.get("character_id")
    character_b_id = state.get("character_b_id")
    if character_id or character_b_id:
        db_session = config.get("configurable", {}).get("db") if config else None
        if db_session:
            _populate_character_actions(scenes, character_id, character_b_id, db_session)

    return {
        "final_scenes": scenes,
        "sound_recommendation": sound_rec,
        "copyright_result": copyright_result,
    }


def _populate_character_actions(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None,
    db,
) -> None:
    """context_tags → character_actions 변환 (finalize 단계)."""
    try:
        from services.characters import auto_populate_character_actions

        auto_populate_character_actions(scenes, character_id, character_b_id, db)
        actions_count = sum(1 for s in scenes if s.get("character_actions"))
        logger.info("[LangGraph] Finalize: character_actions populated for %d/%d scenes", actions_count, len(scenes))
    except Exception:
        logger.warning("[LangGraph] Finalize: character_actions 변환 실패 (non-fatal)", exc_info=True)
