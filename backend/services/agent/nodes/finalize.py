"""Finalize 노드 — Quick은 패스스루, Full은 Production 결과를 병합한다."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import (
    DEFAULT_GAZE_TAG,
    DEFAULT_POSE_TAG,
    DEFAULT_SCENE_NEGATIVE_PROMPT,
    DURATION_DEFICIT_THRESHOLD,
    logger,
)
from database import get_db_session
from services.agent.state import ScriptState

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


def _inject_negative_prompts(scenes: list[dict]) -> None:
    """빈 negative_prompt에 기본값을 주입하고, LLM의 negative_prompt_extra를 병합한다."""
    for scene in scenes:
        base = scene.get("negative_prompt") or DEFAULT_SCENE_NEGATIVE_PROMPT
        extra = scene.get("negative_prompt_extra")
        if extra:
            base = f"{base}, {extra}"
        scene["negative_prompt"] = base


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
    """캐릭터 씬의 context_tags에 pose/gaze/expression 기본값을 주입한다.

    Gemini가 context_tags를 누락하면 character_actions 변환이 실패하므로,
    기본값을 채워서 최소한의 character_actions가 생성되도록 한다.
    Narrator 씬(배경샷)은 캐릭터가 없으므로 건너뛴다.
    """
    from config import DEFAULT_EXPRESSION_TAG  # noqa: PLC0415

    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker == "Narrator":
            continue

        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {
                "pose": DEFAULT_POSE_TAG,
                "gaze": DEFAULT_GAZE_TAG,
                "expression": DEFAULT_EXPRESSION_TAG,
            }
            continue

        if not ctx.get("pose"):
            ctx["pose"] = DEFAULT_POSE_TAG
        if not ctx.get("gaze"):
            ctx["gaze"] = DEFAULT_GAZE_TAG
        if not ctx.get("expression"):
            ctx["expression"] = DEFAULT_EXPRESSION_TAG


def _normalize_environment_tags(scenes: list[dict]) -> None:
    """context_tags.setting → context_tags.environment 정규화."""
    for scene in scenes:
        ctx = scene.get("context_tags")
        if not ctx:
            continue
        if "setting" in ctx and "environment" not in ctx:
            ctx["environment"] = ctx.pop("setting")


def _validate_controlnet_poses(scenes: list[dict]) -> None:
    """controlnet_pose 값이 POSE_MAPPING 키에 있는지 검증. 무효 시 None 리셋."""
    from services.controlnet import POSE_MAPPING  # noqa: PLC0415

    valid_poses = set(POSE_MAPPING.keys())
    for scene in scenes:
        pose = scene.get("controlnet_pose")
        if not pose:
            continue
        if pose not in valid_poses:
            # Gemini가 언더바 형식으로 반환할 수 있으므로 공백으로 변환 후 재검증
            normalized = pose.replace("_", " ")
            if normalized in valid_poses:
                scene["controlnet_pose"] = normalized
            else:
                logger.warning("[Finalize] Invalid controlnet_pose '%s' → reset to None", pose)
                scene["controlnet_pose"] = None


def _validate_ip_adapter_weights(scenes: list[dict]) -> None:
    """ip_adapter_weight 범위 [0.0, 1.0] 클램프."""
    for scene in scenes:
        w = scene.get("ip_adapter_weight")
        if w is None:
            continue
        clamped = max(0.0, min(1.0, float(w)))
        if clamped != w:
            logger.warning("[Finalize] ip_adapter_weight %.2f → clamped to %.2f", w, clamped)
            scene["ip_adapter_weight"] = clamped


def _validate_ken_burns_presets(scenes: list[dict]) -> None:
    """씬별 ken_burns_preset 검증. 무효 시 제거, 누락 시 감정 기반 자동 배정."""
    from services.motion import VALID_PRESET_NAMES, suggest_ken_burns_preset  # noqa: PLC0415

    for i, scene in enumerate(scenes):
        preset = scene.get("ken_burns_preset")
        if preset and preset not in VALID_PRESET_NAMES:
            logger.warning("[Finalize] Invalid ken_burns_preset '%s' → removed", preset)
            scene.pop("ken_burns_preset", None)
            preset = None
        if not preset:
            emotion = (scene.get("context_tags") or {}).get("emotion")
            if emotion:
                scene["ken_burns_preset"] = suggest_ken_burns_preset(emotion, seed=i)
                logger.info(
                    "[Finalize] ken_burns_preset auto-assigned: scene %d → %s (emotion=%s)",
                    i,
                    scene["ken_burns_preset"],
                    emotion,
                )


def _auto_populate_scene_flags(scenes: list[dict], character_id: int | None) -> None:
    """씬별 생성 플래그(use_controlnet, use_ip_adapter, multi_gen_enabled) 자동 할당.

    이미 값이 있는 필드는 덮어쓰지 않는다 (Cinematographer 명시값 보존).
    """
    from config import (  # noqa: PLC0415
        DEFAULT_CONTROLNET_WEIGHT,
        DEFAULT_IP_ADAPTER_WEIGHT,
        DEFAULT_MULTI_GEN_ENABLED,
    )

    for scene in scenes:
        is_narrator = scene.get("speaker") == "Narrator"
        has_pose = bool(scene.get("controlnet_pose"))

        if scene.get("use_controlnet") is None:
            scene["use_controlnet"] = has_pose and not is_narrator
        if scene.get("controlnet_weight") is None and scene["use_controlnet"]:
            scene["controlnet_weight"] = DEFAULT_CONTROLNET_WEIGHT

        if scene.get("use_ip_adapter") is None:
            scene["use_ip_adapter"] = bool(character_id) and not is_narrator
        if scene.get("ip_adapter_weight") is None and scene["use_ip_adapter"]:
            scene["ip_adapter_weight"] = DEFAULT_IP_ADAPTER_WEIGHT

        if scene.get("multi_gen_enabled") is None:
            scene["multi_gen_enabled"] = DEFAULT_MULTI_GEN_ENABLED

    populated = sum(1 for s in scenes if s.get("use_controlnet") or s.get("use_ip_adapter"))
    logger.info("[Finalize] Scene flags populated: %d/%d scenes with generation overrides", populated, len(scenes))


def _flatten_tts_designs(scenes: list[dict]) -> None:
    """tts_design dict → voice_design_prompt, head_padding, tail_padding 분해."""
    for scene in scenes:
        tts = scene.pop("tts_design", None)
        if not tts or tts.get("skip"):
            continue
        if vdp := tts.get("voice_design_prompt"):
            scene["voice_design_prompt"] = vdp
        pacing = tts.get("pacing") or {}
        if (hp := pacing.get("head_padding")) is not None:
            scene["head_padding"] = hp
        if (tp := pacing.get("tail_padding")) is not None:
            scene["tail_padding"] = tp


def _ensure_minimum_duration(scenes: list[dict], target_duration: int, language: str) -> None:
    """총 duration이 목표의 85% 미만이면 비례 재분배한다."""
    total = sum(s.get("duration", 0) for s in scenes)
    if total >= target_duration * DURATION_DEFICIT_THRESHOLD or total <= 0 or not scenes:
        return

    from services.agent.nodes._revise_expand import redistribute_durations

    redistribute_durations(scenes, target_duration, language)
    new_total = sum(s.get("duration", 0) for s in scenes)
    logger.info("[Finalize] Duration 보정: %.1fs → %.1fs (target=%ds)", total, new_total, target_duration)


async def finalize_node(state: ScriptState, config: RunnableConfig) -> dict:
    """Quick: draft → final 패스스루. Full: Production 결과 병합 + character_actions 변환."""
    # 에러 상태이면 즉시 반환 (에러 메시지 보존)
    if state.get("error"):
        logger.warning("[LangGraph] Finalize: 에러 상태 전파 → %s", state.get("error"))
        return {"error": state.get("error")}

    sound_rec: dict | None = None
    copyright_result: dict | None = None

    if "production" not in (state.get("skip_stages") or []) and state.get("cinematographer_result"):
        scenes, sound_rec, copyright_result = _merge_production_results(state)
    else:
        scenes = [dict(s) for s in (state.get("draft_scenes") or [])]

    _inject_negative_prompts(scenes)
    _inject_default_context_tags(scenes)
    _normalize_environment_tags(scenes)
    _validate_controlnet_poses(scenes)
    _validate_ip_adapter_weights(scenes)
    _validate_ken_burns_presets(scenes)
    _auto_populate_scene_flags(scenes, state.get("character_id"))
    _flatten_tts_designs(scenes)

    # Duration 최종 보정 (Review/Revise 경유 후에도 부족할 수 있음)
    target_duration = state.get("duration", 0)
    if target_duration > 0:
        _ensure_minimum_duration(scenes, target_duration, state.get("language", "Korean"))

    # character_actions 변환: context_tags → ControlNet 포즈/표정 데이터
    character_id = state.get("character_id")
    character_b_id = state.get("character_b_id")
    if character_id or character_b_id:
        with get_db_session() as db_session:
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
