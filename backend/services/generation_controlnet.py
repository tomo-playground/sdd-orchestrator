"""ControlNet + IP-Adapter application for generation pipeline.

Extracted from generation.py for module size compliance.
Environment pinning refactored for reduced nesting depth (7→3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import (
    DEFAULT_IP_ADAPTER_GUIDANCE_END_VPRED,
    logger,
)
from services.controlnet import (
    build_controlnet_args,
    detect_pose_from_prompt,
    load_pose_reference,
    load_reference_image,
)
from services.prompt import split_prompt_tokens

if TYPE_CHECKING:
    from schemas import SceneGenerateRequest
    from services.generation_context import GenerationContext


def apply_controlnet(payload: dict, ctx: GenerationContext, db) -> None:
    """Apply ControlNet + IP-Adapter to payload. Writes to ctx.controlnet_used, ctx.ip_adapter_used."""
    req = ctx.request

    # 2P: ControlNet Pose 적용 + IP-Adapter (scene_2p.json에 IP-Adapter 노드 포함)
    # req.character_b_id도 검사: prepare_prompt 실패 시 ctx.character_b_id가 None일 수 있음
    if getattr(ctx, "character_b_id", None) is not None or getattr(req, "character_b_id", None) is not None:
        _apply_2p_pose(req, ctx, payload, db)
        strategy = ctx.consistency
        _apply_ip_adapter(ctx, strategy, [], db)
        _inject_ip_adapter_payload(payload, ctx, req, db)
        return

    strategy = ctx.consistency
    controlnet_args_list: list[dict] = []

    _apply_pose_control(req, ctx, controlnet_args_list, db)
    _apply_reference_only(req, ctx, strategy, controlnet_args_list, db)
    _apply_environment(req, ctx, controlnet_args_list, db)
    _apply_ip_adapter(ctx, strategy, controlnet_args_list, db)

    # Apply combined ControlNet args to payload
    if controlnet_args_list:
        payload.setdefault("alwayson_scripts", {})["controlnet"] = {"args": controlnet_args_list}
        for i, arg in enumerate(controlnet_args_list):
            debug_arg = {
                k: (v[:50] + "..." if k == "image" and isinstance(v, str) and len(v) > 50 else v)
                for k, v in arg.items()
            }
            logger.info("🔧 [ControlNet Arg %d] %s", i, debug_arg)

    # ComfyUI: IP-Adapter payload 주입 (워크플로우 노드 변수로 변환됨)
    _inject_ip_adapter_payload(payload, ctx, req, db)


def _apply_2p_pose(req: SceneGenerateRequest, ctx: GenerationContext, payload: dict, db) -> None:
    """Apply 2P ControlNet Pose. Sets _pose_image_b64, _pose_name, _controlnet_strength in payload."""
    from config import CONTROLNET_2P_DEFAULT_POSE, CONTROLNET_2P_STRENGTH  # noqa: PLC0415
    from services.controlnet import detect_2p_pose_from_prompt, load_2p_pose_reference  # noqa: PLC0415

    # Pose selection priority: explicit → prompt → default
    pose_name = getattr(req, "controlnet_pose", None)
    if pose_name:
        from services.controlnet import POSE_2P_MAPPING  # noqa: PLC0415

        if pose_name not in POSE_2P_MAPPING:
            logger.warning("👥 [2P Pose] '%s' not in POSE_2P_MAPPING, falling back to default", pose_name)
            pose_name = None

    if not pose_name:
        pose_name = detect_2p_pose_from_prompt(ctx.prompt)

    if not pose_name:
        pose_name = CONTROLNET_2P_DEFAULT_POSE

    pose_b64 = load_2p_pose_reference(pose_name)
    if not pose_b64:
        logger.warning("👥 [2P Pose] Pose asset not found for '%s' — falling back to scene_single", pose_name)
        payload["_comfy_workflow"] = "scene_single"
        return

    payload["_pose_image_b64"] = pose_b64
    payload["_pose_name"] = pose_name
    # PoC 검증 결과 0.7 최적 — 사용자 오버라이드 미지원 (의도적 고정)
    payload["_controlnet_strength"] = CONTROLNET_2P_STRENGTH
    ctx.controlnet_used = pose_name
    logger.info("👥 [2P Pose] Using pose: %s (strength=%.1f)", pose_name, CONTROLNET_2P_STRENGTH)


def _apply_pose_control(req: SceneGenerateRequest, ctx: GenerationContext, args: list, db=None) -> None:
    """Apply OpenPose ControlNet if requested."""
    if not req.use_controlnet:
        return
    pose_name = req.controlnet_pose
    # Phase 3-A: character_actions pose 힌트 활용 (explicit pose 이전)
    if not pose_name and req.scene_id and db:
        pose_name = _get_pose_from_character_actions(req.scene_id, db)
    if not pose_name:
        pose_name = detect_pose_from_prompt(ctx.prompt)
    if not pose_name:
        return
    pose_image = load_pose_reference(pose_name)
    if not pose_image:
        return
    args.append(
        build_controlnet_args(
            input_image=pose_image,
            model="openpose",
            weight=req.controlnet_weight,
            control_mode=req.controlnet_control_mode,
        )
    )
    ctx.controlnet_used = pose_name
    logger.info("🎭 [ControlNet] Using pose: %s (weight=%.1f)", pose_name, req.controlnet_weight)


def _apply_reference_only(req, ctx: GenerationContext, strategy, args: list, db) -> None:
    """Apply reference-only ControlNet (skipped when IP-Adapter is active, decided by strategy)."""
    if not (req.character_id and strategy.reference_only_enabled):
        return
    ref_image = load_reference_image(ctx.character_name or "", db=db)
    if not ref_image:
        return
    args.append(
        build_controlnet_args(
            input_image=ref_image, model="reference", weight=strategy.reference_only_weight, control_mode="Balanced"
        )
    )
    logger.info("🎨 [Reference-only] Enabled for character consistency (weight=%.2f)", strategy.reference_only_weight)


def _apply_environment(req: SceneGenerateRequest, ctx: GenerationContext, args: list, db) -> None:
    """Apply environment atmosphere via Reference AdaIN with conflict detection."""
    from config import ENVIRONMENT_REFERENCE_ENABLED  # noqa: PLC0415

    if not ENVIRONMENT_REFERENCE_ENABLED:
        return
    if not req.environment_reference_id:
        return
    is_no_humans = "no_humans" in ctx.prompt
    if is_no_humans:
        logger.info("🏠 [Environment Reference] Skipped for no_humans scene (Narrator)")
        return

    # Classify indoor/outdoor from environment tags for weight adjustment
    env_tags = _extract_env_tags(req, db)
    location_type = classify_indoor_outdoor(env_tags)
    _apply_environment_pinning(req, args, ctx.warnings, db, location_type=location_type, ctx=ctx)


def _apply_ip_adapter(ctx: GenerationContext, strategy, args: list, db) -> None:
    """Apply IP-Adapter for style/identity transfer (strategy-driven).

    ComfyUI: builds ctx._ip_adapter_payload dict (consumed by ComfyUIClient.txt2img).
    Legacy alwayson_scripts args are still appended for backward compat (ignored by ComfyUI).
    """
    if not (strategy.ip_adapter_enabled and strategy.ip_adapter_reference):
        return
    ref_image = load_reference_image(strategy.ip_adapter_reference, db=db)
    if not ref_image:
        logger.warning(
            "🧑 [IP-Adapter] Reference image load failed for '%s' — skipping IP-Adapter",
            strategy.ip_adapter_reference,
        )
        ctx.warnings.append(f"IP-Adapter reference load failed: {strategy.ip_adapter_reference}")
        return
    # Safety clamp: pose direction → weight limit
    from services.controlnet import clamp_ip_adapter_weight  # noqa: PLC0415

    effective_weight = clamp_ip_adapter_weight(strategy.ip_adapter_weight, ctx.controlnet_used)
    end_at = (
        strategy.ip_adapter_guidance_end
        if strategy.ip_adapter_guidance_end is not None
        else DEFAULT_IP_ADAPTER_GUIDANCE_END_VPRED
    )

    if strategy.ip_adapter_guidance_start and strategy.ip_adapter_guidance_start > 0.0:
        logger.info(
            "🧑 [IP-Adapter] guidance_start=%.2f ignored — hardcoded to 0.0 in ComfyUI workflow",
            strategy.ip_adapter_guidance_start,
        )

    # ComfyUI: _ip_adapter_payload → ComfyUIClient가 워크플로우 노드 변수로 주입
    ctx._ip_adapter_payload = {
        "image_b64": ref_image,
        "name": strategy.ip_adapter_reference,
        "weight": effective_weight,
        "end_at": end_at,
    }
    ctx.ip_adapter_used = strategy.ip_adapter_reference
    logger.info(
        "🧑 [IP-Adapter] Using reference: %s (weight=%.2f, end_at=%.2f)",
        strategy.ip_adapter_reference,
        effective_weight,
        end_at,
    )


def _inject_ip_adapter_payload(payload: dict, ctx: GenerationContext, req: SceneGenerateRequest, db) -> None:
    """Inject IP-Adapter payload including background reference (SP-115)."""
    from config import (  # noqa: PLC0415
        BG_IP_ADAPTER_ENABLED,
        DEFAULT_BG_IP_ADAPTER_END_AT,
        DEFAULT_BG_IP_ADAPTER_WEIGHT,
    )

    ip_payload = ctx._ip_adapter_payload

    # Background IP-Adapter: load reference if available
    if BG_IP_ADAPTER_ENABLED:
        bg_b64 = _load_bg_reference(req, db)
        if bg_b64:
            if ip_payload is None:
                ip_payload = {}
            ip_payload["bg_image_b64"] = bg_b64
            ip_payload["bg_weight"] = DEFAULT_BG_IP_ADAPTER_WEIGHT
            ip_payload["bg_end_at"] = DEFAULT_BG_IP_ADAPTER_END_AT
            logger.info(
                "🏠 [BG IP-Adapter] Loaded environment reference for env_ref_id=%s", req.environment_reference_id
            )

    if ip_payload:
        payload["_ip_adapter"] = ip_payload


def _load_bg_reference(req: SceneGenerateRequest, db) -> str | None:
    """Load background reference image as base64 from environment_reference_id."""
    if not req.environment_reference_id:
        return None
    import base64  # noqa: PLC0415
    import os  # noqa: PLC0415

    from models.media_asset import MediaAsset  # noqa: PLC0415

    asset = db.query(MediaAsset).filter(MediaAsset.id == req.environment_reference_id).first()
    if not asset or not asset.local_path:
        return None
    if not os.path.exists(asset.local_path):
        logger.warning("🏠 [BG IP-Adapter] Asset file not found: %s", asset.local_path)
        return None
    try:
        with open(asset.local_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error("🏠 [BG IP-Adapter] Failed to load asset: %s", e)
        return None


# ── Cinematic tag suppression (AdaIN conflict prevention) ─────────────


def _canonical_prompt_tag(token: str) -> str:
    """Extract base tag from weighted syntax like (bokeh:1.2)."""
    t = token.strip()
    if t.startswith("(") and t.endswith(")"):
        t = t[1:-1].strip()
    head, sep, tail = t.rpartition(":")
    if sep:
        try:
            float(tail)
            t = head.strip()
        except ValueError:
            pass
    return t


def _suppress_cinematic_for_adain(ctx: GenerationContext) -> list[str]:
    """Reference AdaIN 활성 시 충돌 시네마틱 태그를 ctx.prompt에서 제거.

    Returns:
        제거된 태그 리스트 (빈 리스트 = 변경 없음).
    """
    from config import REFERENCE_ADAIN_CONFLICTING_TAGS  # noqa: PLC0415

    tokens = split_prompt_tokens(ctx.prompt)
    removed: list[str] = []
    filtered: list[str] = []
    for token in tokens:
        if _canonical_prompt_tag(token) in REFERENCE_ADAIN_CONFLICTING_TAGS:
            removed.append(token)
        else:
            filtered.append(token)
    if removed:
        ctx.prompt = ", ".join(filtered)
    return removed


# ── Environment Pinning helpers (nesting 7→3) ────────────────────────


def _apply_environment_pinning(
    request: SceneGenerateRequest,
    controlnet_args_list: list,
    warnings: list[str],
    db,
    location_type: str | None = None,
    ctx: GenerationContext | None = None,
) -> None:
    """Handle environment reference pinning with conflict detection."""
    env_asset = _load_env_asset(request.environment_reference_id, db)
    if not env_asset:
        return

    conflict = _detect_env_conflict(env_asset, request, db)
    if conflict:
        msg = f"장소 변화가 감지되어 배경 고정이 자동으로 해제되었습니다. ({conflict})"
        logger.warning("⚠️ [Environment Pinning] %s", msg)
        warnings.append(msg)
        return

    # AdaIN 적용 먼저, 성공 시에만 태그 억제
    applied = _apply_reference_adain_from_asset(env_asset, request, controlnet_args_list, location_type)
    if applied and ctx:
        removed = _suppress_cinematic_for_adain(ctx)
        if removed:
            msg = f"⚠️ AdaIN 충돌 방지: 시네마틱 태그 억제됨 — {', '.join(removed)}"
            logger.warning("[AdaIN Cinematic Filter] Stripped: %s", removed)
            warnings.append(msg)


def _load_env_asset(env_ref_id: int, db):
    """Load environment media asset from DB."""
    from models.media_asset import MediaAsset

    asset = db.query(MediaAsset).filter(MediaAsset.id == env_ref_id).first()
    if not asset or not asset.local_path:
        return None
    return asset


def _detect_env_conflict(env_asset, request: SceneGenerateRequest, db) -> str | None:
    """Detect location conflict between reference scene and current prompt.

    Returns conflict reason string if conflict detected, None otherwise.
    Also logs cinematic tag overlap with AdaIN conflicting tags (informational).
    """
    if env_asset.owner_type != "scene":
        return None

    from models.scene import Scene

    ref_scene = db.query(Scene).filter(Scene.id == env_asset.owner_id, Scene.deleted_at.is_(None)).first()
    if not ref_scene:
        return None

    # P2: cinematic 충돌 감지 (정보성 — AdaIN 적용 자체는 중단하지 않음)
    _detect_cinematic_conflict(request)

    return _check_tag_conflict(ref_scene, request, db)


def _detect_cinematic_conflict(request: SceneGenerateRequest) -> None:
    """Log cinematic tags that conflict with Reference AdaIN (informational)."""
    from config import REFERENCE_ADAIN_CONFLICTING_TAGS  # noqa: PLC0415

    context_tags = getattr(request, "context_tags", None)
    if not context_tags or not isinstance(context_tags, dict):
        return
    cinematic = context_tags.get("cinematic", [])
    if not cinematic:
        return
    overlap = set(cinematic) & REFERENCE_ADAIN_CONFLICTING_TAGS
    if overlap:
        logger.info("[AdaIN Conflict Detect] cinematic tags overlap with AdaIN: %s", list(overlap))


def _check_tag_conflict(ref_scene, request: SceneGenerateRequest, db) -> str | None:
    """Check environment tag mismatch between reference and current scene."""
    from services.prompt.composition import LAYER_ENVIRONMENT, PromptBuilder

    ref_env = set(ref_scene.context_tags.get("environment", [])) if ref_scene.context_tags else set()
    if not ref_env:
        return None

    builder = PromptBuilder(db)
    curr_tokens = split_prompt_tokens(request.prompt)
    curr_tag_info = builder.get_tag_info(curr_tokens)
    curr_env = {tag for tag, info in curr_tag_info.items() if info.get("layer") == LAYER_ENVIRONMENT}

    if curr_env and not (ref_env & curr_env):
        return f"Location mismatch: {list(ref_env)} vs {list(curr_env)}"
    return None


def classify_indoor_outdoor(env_tags: list[str]) -> str | None:
    """Classify indoor/outdoor from environment tags. Returns None for mixed/unknown."""
    from config_prompt import INDOOR_LOCATION_TAGS, OUTDOOR_LOCATION_TAGS

    has_indoor = any(t in INDOOR_LOCATION_TAGS for t in env_tags)
    has_outdoor = any(t in OUTDOOR_LOCATION_TAGS for t in env_tags)
    if has_indoor and not has_outdoor:
        return "indoor"
    if has_outdoor and not has_indoor:
        return "outdoor"
    return None


def _extract_env_tags(req: SceneGenerateRequest, db) -> list[str]:
    """Extract environment tags from scene's context_tags."""
    if not req.scene_id:
        return []
    try:
        from models.scene import Scene

        scene = db.query(Scene).filter(Scene.id == req.scene_id, Scene.deleted_at.is_(None)).first()
        if scene and scene.context_tags:
            env = scene.context_tags.get("environment", [])
            return env if isinstance(env, list) else []
    except Exception:
        logger.warning("[AdaIN] Failed to extract env tags for scene %s", req.scene_id, exc_info=True)
    return []


def _apply_reference_adain_from_asset(
    env_asset, request: SceneGenerateRequest, controlnet_args_list: list, location_type: str | None = None
) -> bool:
    """Apply Reference AdaIN from environment asset for atmosphere/color transfer.

    Weight varies by location type: indoor=0.30, outdoor=0.25, default=0.35.

    Returns:
        True if AdaIN was applied successfully, False otherwise.
    """
    import base64
    import os

    from config import (
        REFERENCE_ADAIN_GUIDANCE_END,
        REFERENCE_ADAIN_WEIGHT,
        REFERENCE_ADAIN_WEIGHT_INDOOR,
        REFERENCE_ADAIN_WEIGHT_OUTDOOR,
    )

    if not os.path.exists(env_asset.local_path):
        return False

    weight = REFERENCE_ADAIN_WEIGHT
    if location_type == "indoor":
        weight = REFERENCE_ADAIN_WEIGHT_INDOOR
    elif location_type == "outdoor":
        weight = REFERENCE_ADAIN_WEIGHT_OUTDOOR

    try:
        with open(env_asset.local_path, "rb") as f:
            env_base64 = base64.b64encode(f.read()).decode("utf-8")
        controlnet_args_list.append(
            {
                "enabled": True,
                "image": env_base64,
                "module": "reference_adain",
                "model": "None",
                "weight": weight,
                "control_mode": "My prompt is more important",
                "pixel_perfect": False,
                "guidance_start": 0.0,
                "guidance_end": REFERENCE_ADAIN_GUIDANCE_END,
                "processor_res": -1,
                "threshold_a": -1,
                "threshold_b": -1,
            }
        )
        logger.info(
            "🏠 [Environment Reference AdaIN] Enabled using asset %d (weight=%.2f, location=%s, guidance_end=%.2f)",
            request.environment_reference_id,
            weight,
            location_type or "default",
            REFERENCE_ADAIN_GUIDANCE_END,
        )
        return True
    except Exception as e:
        logger.error("❌ [Environment Reference AdaIN] Failed to load asset: %s", e)
        return False


# ── Character Actions pose hint ───────────────────────────────────


def _get_pose_from_character_actions(scene_id: int, db) -> str | None:
    """Retrieve pose tag name from character_actions for ControlNet hint."""
    try:
        from models.associations import SceneCharacterAction
        from models.tag import Tag

        rows = (
            db.query(Tag.name)
            .join(SceneCharacterAction, SceneCharacterAction.tag_id == Tag.id)
            .filter(
                SceneCharacterAction.scene_id == scene_id,
                Tag.group_name == "pose",
            )
            .limit(1)
            .all()
        )
        if rows:
            logger.info("[ControlNet] pose_hint from character_actions: %s", rows[0][0])
            return rows[0][0]
    except Exception:
        logger.debug("[ControlNet] pose_hint lookup failed", exc_info=True)
    return None
