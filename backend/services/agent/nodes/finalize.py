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


_QUALITY_TAG_FIXES = {"high_quality": "best_quality"}


def _sanitize_quality_tags(scenes: list[dict]) -> None:
    """비표준 quality 태그를 Danbooru 표준으로 치환한다 (e.g. high_quality → best_quality)."""
    for scene in scenes:
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue
        tokens = [t.strip() for t in prompt.split(",")]
        scene["image_prompt"] = ", ".join(_QUALITY_TAG_FIXES[t] if t in _QUALITY_TAG_FIXES else t for t in tokens)


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
    expression은 emotion 필드에서 파생을 시도하고, 실패 시 기본값.
    Narrator 씬(배경샷)은 캐릭터가 없으므로 건너뛴다.
    """
    from config import DEFAULT_EXPRESSION_TAG  # noqa: PLC0415

    from ._context_tag_utils import derive_expression_from_emotion

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
            emotion = ctx.get("emotion")
            derived = derive_expression_from_emotion(emotion) if emotion else None
            ctx["expression"] = derived or DEFAULT_EXPRESSION_TAG


def _inject_writer_plan_emotions(scenes: list[dict], writer_plan: dict | None) -> None:
    """writer_plan.emotional_arc에서 빈 context_tags.emotion을 채운다."""
    if not writer_plan:
        return
    arc = writer_plan.get("emotional_arc", [])
    if not arc:
        return
    for i, scene in enumerate(scenes):
        if i >= len(arc):
            break
        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {"emotion": arc[i]}
        elif not ctx.get("emotion"):
            ctx["emotion"] = arc[i]


def _normalize_environment_tags(scenes: list[dict]) -> None:
    """context_tags.setting → context_tags.environment 정규화."""
    for scene in scenes:
        ctx = scene.get("context_tags")
        if not ctx:
            continue
        if "setting" in ctx and "environment" not in ctx:
            ctx["environment"] = ctx.pop("setting")


def _build_scene_to_tags_map(writer_plan: dict) -> dict[int, list[str]]:
    """writer_plan.locations에서 scene_idx → tags 매핑을 구축한다."""
    idx_to_tags: dict[int, list[str]] = {}
    for loc in writer_plan.get("locations", []):
        for idx in loc.get("scenes", []):
            idx_to_tags[idx] = loc.get("tags", [])
    return idx_to_tags


def _inject_location_map_tags(scenes: list[dict], writer_plan: dict | None) -> None:
    """writer_plan.locations 기반으로 각 씬의 context_tags.environment에 구체 태그를 주입한다.

    LLM이 generic 태그(indoors/outdoors)만 생성해도, Location Map의 구체 태그로 보강하여
    SD가 일관된 배경을 생성하도록 한다.
    """
    from config_prompt import GENERIC_LOCATION_TAGS  # noqa: PLC0415

    if not writer_plan or not writer_plan.get("locations"):
        return

    idx_to_tags = _build_scene_to_tags_map(writer_plan)

    for i, scene in enumerate(scenes):
        loc_tags = idx_to_tags.get(i)
        if not loc_tags:
            continue

        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {"environment": list(loc_tags)}
            continue

        env = ctx.get("environment")
        if env is None:
            env = []
        elif isinstance(env, str):
            env = [env]
        else:
            env = list(env)

        def _norm(tag: str) -> str:
            return tag.lower().replace(" ", "_").strip()

        existing_norms = {_norm(t) for t in env}

        # 구체 태그를 앞에, generic 태그를 뒤에 배치
        specific_new = [t for t in loc_tags if _norm(t) not in existing_norms and _norm(t) not in GENERIC_LOCATION_TAGS]
        generic_new = [t for t in loc_tags if _norm(t) not in existing_norms and _norm(t) in GENERIC_LOCATION_TAGS]

        specific_existing = [t for t in env if _norm(t) not in GENERIC_LOCATION_TAGS]
        generic_existing = [t for t in env if _norm(t) in GENERIC_LOCATION_TAGS]

        ctx["environment"] = specific_existing + specific_new + generic_existing + generic_new


def _inject_location_negative_tags(scenes: list[dict], writer_plan: dict | None) -> None:
    """Location Map 기반으로 indoor/outdoor 씬의 negative_prompt_extra에 반대 태그를 추가한다.

    indoor 장소 씬 → negative에 'outdoors', outdoor 장소 씬 → negative에 'indoors'.
    """
    from config_prompt import INDOOR_LOCATION_TAGS, OUTDOOR_LOCATION_TAGS  # noqa: PLC0415

    if not writer_plan or not writer_plan.get("locations"):
        return

    idx_to_tags = _build_scene_to_tags_map(writer_plan)

    for i, scene in enumerate(scenes):
        loc_tags = idx_to_tags.get(i)
        if not loc_tags:
            continue

        tag_norms = {t.lower().replace(" ", "_").strip() for t in loc_tags}
        is_indoor = bool(tag_norms & INDOOR_LOCATION_TAGS)
        is_outdoor = bool(tag_norms & OUTDOOR_LOCATION_TAGS)

        if is_indoor and not is_outdoor:
            neg_tag = "outdoors"
        elif is_outdoor and not is_indoor:
            neg_tag = "indoors"
        else:
            continue

        existing = scene.get("negative_prompt_extra") or ""
        existing_norms = {t.strip().lower() for t in existing.split(",") if t.strip()}
        if neg_tag not in existing_norms:
            scene["negative_prompt_extra"] = f"{existing}, {neg_tag}".strip(", ") if existing else neg_tag


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

    _sanitize_quality_tags(scenes)
    _inject_negative_prompts(scenes)

    from ._context_tag_utils import check_camera_diversity, validate_context_tag_categories

    validate_context_tag_categories(scenes)
    _inject_writer_plan_emotions(scenes, state.get("writer_plan"))
    _inject_default_context_tags(scenes)
    _normalize_environment_tags(scenes)
    _inject_location_map_tags(scenes, state.get("writer_plan"))
    _inject_location_negative_tags(scenes, state.get("writer_plan"))

    # 미분류 태그 LLM 사전 분류 (이미지 생성 전)
    from config_pipelines import FEATURE_TAG_LLM_CLASSIFICATION

    if FEATURE_TAG_LLM_CLASSIFICATION:
        from ._tag_classification import classify_unknown_scene_tags

        try:
            with get_db_session() as db_session:
                await classify_unknown_scene_tags(scenes, db_session)
        except Exception:
            logger.warning("[Finalize] LLM tag classification failed (non-fatal)", exc_info=True)

    from ._finalize_validators import (
        validate_controlnet_poses,
        validate_ip_adapter_weights,
        validate_ken_burns_presets,
    )

    validate_controlnet_poses(scenes)
    validate_ip_adapter_weights(scenes)
    validate_ken_burns_presets(scenes)
    check_camera_diversity(scenes)
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
