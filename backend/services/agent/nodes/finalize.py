"""Finalize 노드 — Quick은 패스스루, Full은 Production 결과를 병합한다."""

from __future__ import annotations

from config import logger
from services.agent.state import ScriptState


def _merge_production_results(state: ScriptState) -> list[dict]:
    """cinematographer_result.scenes에 tts/sound/copyright 결과를 병합한다."""
    cinema = state.get("cinematographer_result") or {}
    scenes = [dict(s) for s in cinema.get("scenes", [])]

    tts_designs = (state.get("tts_designer_result") or {}).get("tts_designs", [])
    sound_rec = (state.get("sound_designer_result") or {}).get("recommendation")
    copyright_result = state.get("copyright_reviewer_result")

    # TTS 디자인을 씬별로 병합
    for i, scene in enumerate(scenes):
        if i < len(tts_designs):
            scene["tts_design"] = tts_designs[i]

    # Sound/Copyright는 전체 결과로 첫 번째 씬에 메타데이터 추가
    if scenes:
        if sound_rec:
            scenes[0]["_sound_recommendation"] = sound_rec
        if copyright_result:
            scenes[0]["_copyright_result"] = copyright_result

    logger.info("[LangGraph] Finalize (Full): %d scenes 병합 완료", len(scenes))
    return scenes


async def finalize_node(state: ScriptState) -> dict:
    """Quick: draft → final 패스스루. Full: Production 결과 병합."""
    mode = state.get("mode", "quick")
    if mode == "full" and state.get("cinematographer_result"):
        return {"final_scenes": _merge_production_results(state)}
    return {"final_scenes": state.get("draft_scenes")}
