"""Finalize 노드 — Quick은 패스스루, Full은 Production 결과를 병합한다."""

from __future__ import annotations

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, logger
from services.agent.state import ScriptState


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


async def finalize_node(state: ScriptState) -> dict:
    """Quick: draft → final 패스스루. Full: Production 결과 병합."""
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
    return {
        "final_scenes": scenes,
        "sound_recommendation": sound_rec,
        "copyright_result": copyright_result,
    }
