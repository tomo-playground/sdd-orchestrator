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


def _apply_tag_aliases(scenes: list[dict]) -> None:
    """DB tag_aliases 기반 자동 교정 — 비표준/모호 태그를 Danbooru 표준으로 치환/제거."""
    from services.keywords.db_cache import TagAliasCache

    # TagAliasCache는 startup 시 초기화됨. 미초기화 시에만 DB 세션 열기.
    if not TagAliasCache._initialized:
        with get_db_session() as db:
            TagAliasCache.initialize(db)

    replaced_count = 0
    removed_count = 0
    split_count = 0
    for scene in scenes:
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue
        tokens = [t.strip() for t in prompt.split(",")]
        result = []
        for t in tokens:
            if not t:
                continue
            replacement = TagAliasCache.get_replacement(t)
            if replacement is ...:
                result.append(t)
            elif replacement is None:
                removed_count += 1
            else:
                parts = [p.strip() for p in replacement.split(",") if p.strip()]
                result.extend(parts)
                replaced_count += 1
                if len(parts) > 1:
                    split_count += 1
        scene["image_prompt"] = ", ".join(result)

    if replaced_count or removed_count:
        logger.info(
            "[Finalize] TagAlias: %d replaced (%d split), %d removed",
            replaced_count,
            split_count,
            removed_count,
        )


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
    import copy  # noqa: PLC0415

    cinema = state.get("cinematographer_result") or {}
    scenes = [copy.deepcopy(s) for s in cinema.get("scenes", [])]

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
    """캐릭터 씬의 context_tags에 pose/gaze/expression/mood 기본값을 주입한다.

    expression은 항상 emotion에서 파생을 시도한다 (Cinematographer가 단일 expression으로
    모든 씬을 채우는 monotony 문제 방지). 파생 실패 시에만 기존값 또는 기본값 사용.
    mood는 빈 경우 emotion에서 자동 생성한다.
    Narrator 씬(배경샷)은 캐릭터가 없으므로 건너뛴다.
    """
    from config import DEFAULT_EXPRESSION_TAG  # noqa: PLC0415

    from ._context_tag_utils import derive_expression_from_emotion, derive_mood_from_emotion

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

        if ctx.get("pose") is None:
            ctx["pose"] = DEFAULT_POSE_TAG
        if ctx.get("gaze") is None:
            ctx["gaze"] = DEFAULT_GAZE_TAG

        # expression: emotion에서 항상 파생 시도 (monotony 방지)
        emotion = ctx.get("emotion")
        derived_expr = derive_expression_from_emotion(emotion) if emotion else None
        if derived_expr:
            ctx["expression"] = derived_expr
        elif ctx.get("expression") is None:
            ctx["expression"] = DEFAULT_EXPRESSION_TAG

        # mood: emotion에서 자동 생성 (빈 mood 해결)
        if ctx.get("mood") is None:
            derived_mood = derive_mood_from_emotion(emotion) if emotion else None
            if derived_mood:
                ctx["mood"] = derived_mood


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


def _copy_scene_level_to_context_tags(scenes: list[dict]) -> None:
    """Cinematographer가 scene-level에 출력한 camera/environment를 context_tags로 복사한다."""
    for scene in scenes:
        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {}
            ctx = scene["context_tags"]

        # camera: scene["camera"] → context_tags["camera"]
        if ctx.get("camera") is None and scene.get("camera"):
            ctx["camera"] = scene["camera"]


def _build_scene_to_tags_map(writer_plan: dict) -> dict[int, list[str]]:
    """writer_plan.locations에서 scene_idx → tags 매핑을 구축한다."""
    from services.agent.state import get_loc_field

    idx_to_tags: dict[int, list[str]] = {}
    for loc in writer_plan.get("locations", []):
        for idx in get_loc_field(loc, "scenes", []):  # type: ignore[union-attr]
            idx_to_tags[idx] = get_loc_field(loc, "tags", [])  # type: ignore[assignment]
    return idx_to_tags


def _inject_location_map_tags(scenes: list[dict], writer_plan: dict | None) -> None:
    """writer_plan.locations 기반으로 각 씬의 context_tags.environment를 교정한다.

    Location Map이 환경 태그의 SSOT. LLM이 생성한 environment 태그 중
    Location Map에 속하지 않는 태그는 할루시네이션으로 간주하여 제거한다.
    """
    from config_prompt import GENERIC_LOCATION_TAGS  # noqa: PLC0415

    if not writer_plan or not writer_plan.get("locations"):
        return

    def _norm(tag: str) -> str:
        return tag.lower().replace(" ", "_").strip()

    idx_to_tags = _build_scene_to_tags_map(writer_plan)

    # Location Map의 모든 유효 환경 태그 수집 (할루시네이션 필터용)
    from services.agent.state import get_loc_field

    all_valid_env: set[str] = set()
    for loc in writer_plan.get("locations", []):
        for t in get_loc_field(loc, "tags", []):  # type: ignore[union-attr]
            all_valid_env.add(_norm(t))
    all_valid_env |= GENERIC_LOCATION_TAGS  # indoors/outdoors 등 generic은 항상 허용

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

        loc_norms = {_norm(t) for t in loc_tags}

        # LLM이 생성한 environment 중 Location Map에 없는 태그 제거 (할루시네이션 방지)
        dropped = [t for t in env if _norm(t) not in all_valid_env]
        if dropped:
            logger.info(
                "[Finalize] Scene %d: 환경 태그 교정 — dropped %s (Location Map에 없음)",
                i,
                dropped,
            )

        kept = [t for t in env if _norm(t) in loc_norms]

        # kept도 specific/generic 분리 (구체 태그 우선 원칙 일관 적용)
        kept_norms = {_norm(k) for k in kept}
        kept_specific = [t for t in kept if _norm(t) not in GENERIC_LOCATION_TAGS]
        kept_generic = [t for t in kept if _norm(t) in GENERIC_LOCATION_TAGS]

        # Location Map 태그 중 아직 없는 것 추가 (구체 → generic 순)
        new_specific = [t for t in loc_tags if _norm(t) not in kept_norms and _norm(t) not in GENERIC_LOCATION_TAGS]
        new_generic = [t for t in loc_tags if _norm(t) not in kept_norms and _norm(t) in GENERIC_LOCATION_TAGS]

        ctx["environment"] = kept_specific + new_specific + kept_generic + new_generic

        # image_prompt에서도 할루시네이션 환경 태그 제거
        if dropped:
            dropped_norms = {_norm(t) for t in dropped}
            prompt = scene.get("image_prompt", "")
            if prompt:
                tokens = [t.strip() for t in prompt.split(",")]
                cleaned = [t for t in tokens if _norm(t) not in dropped_norms]
                if len(cleaned) < len(tokens):
                    scene["image_prompt"] = ", ".join(cleaned)
                    logger.info(
                        "[Finalize] Scene %d: image_prompt에서 환경 태그 %d개 제거",
                        i,
                        len(tokens) - len(cleaned),
                    )


def _inject_location_negative_tags(scenes: list[dict], writer_plan: dict | None) -> None:
    """Location Map 기반으로 indoor/outdoor 씬의 negative_prompt에 반대 태그를 추가한다.

    indoor 장소 씬 → negative에 'outdoors', outdoor 장소 씬 → negative에 'indoors'.
    _inject_negative_prompts() 이후 실행되므로 negative_prompt에 직접 append한다.
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

        existing_neg = scene.get("negative_prompt") or ""
        existing_norms = {t.strip().lower() for t in existing_neg.split(",") if t.strip()}
        if neg_tag not in existing_norms:
            scene["negative_prompt"] = f"{existing_neg}, {neg_tag}" if existing_neg else neg_tag


def _auto_populate_scene_flags(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None = None,
) -> None:
    """씬별 생성 플래그(use_controlnet, use_ip_adapter, multi_gen_enabled) 자동 할당.

    이미 값이 있는 필드는 덮어쓰지 않는다 (Cinematographer 명시값 보존).
    Express 모드처럼 Cinematographer가 스킵된 경우, context_tags.pose에서
    controlnet_pose를 자동 할당하여 ControlNet을 활성화한다.
    Dialogue 구조에서는 speaker B도 character_b_id 기반으로 ControlNet/IP-Adapter 활성화.
    """
    from config import (  # noqa: PLC0415
        DEFAULT_CONTROLNET_WEIGHT,
        DEFAULT_IP_ADAPTER_WEIGHT,
        DEFAULT_MULTI_GEN_ENABLED,
        DEFAULT_POSE_TAG,
    )
    from services.controlnet import POSE_MAPPING  # noqa: PLC0415

    valid_poses = set(POSE_MAPPING.keys())

    for scene in scenes:
        is_narrator = scene.get("speaker") == "Narrator"
        # Dialogue: speaker B uses character_b_id, others use character_id
        scene_char_id = character_b_id if scene.get("speaker") == "B" else character_id

        # controlnet_pose 자동 할당: Cinematographer 미실행 시 context_tags.pose에서 파생
        if not scene.get("controlnet_pose") and not is_narrator and scene_char_id:
            ctx_pose = (scene.get("context_tags") or {}).get("pose", DEFAULT_POSE_TAG)
            if ctx_pose in valid_poses:
                scene["controlnet_pose"] = ctx_pose
            elif ctx_pose and ctx_pose.replace("_", " ") in valid_poses:
                scene["controlnet_pose"] = ctx_pose.replace("_", " ")
            else:
                scene["controlnet_pose"] = DEFAULT_POSE_TAG

        has_pose = bool(scene.get("controlnet_pose"))

        if scene.get("use_controlnet") is None:
            scene["use_controlnet"] = has_pose and not is_narrator
        if scene.get("controlnet_weight") is None and scene["use_controlnet"]:
            scene["controlnet_weight"] = DEFAULT_CONTROLNET_WEIGHT

        if scene.get("use_ip_adapter") is None:
            scene["use_ip_adapter"] = bool(scene_char_id) and not is_narrator
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

    import copy  # noqa: PLC0415

    sound_rec: dict | None = None
    copyright_result: dict | None = None

    if "production" not in (state.get("skip_stages") or []) and state.get("cinematographer_result"):
        scenes, sound_rec, copyright_result = _merge_production_results(state)
    else:
        scenes = [copy.deepcopy(s) for s in (state.get("draft_scenes") or [])]

    _sanitize_quality_tags(scenes)
    _apply_tag_aliases(scenes)
    _inject_negative_prompts(scenes)

    from ._prompt_conflict_resolver import resolve_prompt_conflicts

    resolve_prompt_conflicts(scenes)
    _copy_scene_level_to_context_tags(scenes)

    from ._context_tag_utils import check_camera_diversity, diversify_expressions, validate_context_tag_categories

    validate_context_tag_categories(scenes)
    _inject_writer_plan_emotions(scenes, state.get("writer_plan"))
    _inject_default_context_tags(scenes)
    diversify_expressions(scenes)
    _normalize_environment_tags(scenes)
    _inject_location_map_tags(scenes, state.get("writer_plan"))
    _inject_location_negative_tags(scenes, state.get("writer_plan"))

    # Post-location conflict re-check: positive↔negative 교차 충돌만 재검사
    from ._prompt_conflict_resolver import _resolve_positive_negative_conflicts

    _resolve_positive_negative_conflicts(scenes)

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
    _auto_populate_scene_flags(scenes, state.get("character_id"), state.get("character_b_id"))
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
