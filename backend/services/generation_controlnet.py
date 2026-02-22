"""ControlNet + IP-Adapter application for generation pipeline.

Extracted from generation.py for module size compliance.
Environment pinning refactored for reduced nesting depth (7→3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import logger
from services.controlnet import (
    build_controlnet_args,
    build_ip_adapter_args,
    check_controlnet_available,
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
    strategy = ctx.consistency
    controlnet_args_list: list[dict] = []

    if not check_controlnet_available():
        return

    _apply_pose_control(req, ctx, controlnet_args_list, db)
    _apply_reference_only(req, ctx, strategy, controlnet_args_list, db)
    _apply_environment(req, ctx, controlnet_args_list, db)
    _apply_ip_adapter(ctx, strategy, controlnet_args_list, db)

    # Apply combined ControlNet args to payload
    if controlnet_args_list:
        payload["alwayson_scripts"] = {"controlnet": {"args": controlnet_args_list}}
        for i, arg in enumerate(controlnet_args_list):
            debug_arg = {
                k: (v[:50] + "..." if k == "image" and isinstance(v, str) and len(v) > 50 else v)
                for k, v in arg.items()
            }
            logger.info("🔧 [ControlNet Arg %d] %s", i, debug_arg)


def _apply_pose_control(req: SceneGenerateRequest, ctx: GenerationContext, args: list, db=None) -> None:
    """Apply OpenPose ControlNet if requested."""
    if not req.use_controlnet:
        return
    pose_name = req.controlnet_pose
    # Phase 3-A: character_actions pose 힌트 활용 (explicit pose 이전)
    if not pose_name and req.scene_id and db:
        pose_name = _get_pose_from_character_actions(req.scene_id, db)
    if not pose_name:
        prompt_tags = split_prompt_tokens(ctx.prompt)
        pose_name = detect_pose_from_prompt(prompt_tags)
    if not pose_name:
        return
    pose_image = load_pose_reference(pose_name)
    if not pose_image:
        return
    args.append(
        build_controlnet_args(
            input_image=pose_image, model="openpose", weight=req.controlnet_weight, control_mode="Balanced"
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
    """Apply environment pinning via Canny ControlNet with conflict detection."""
    if not req.environment_reference_id:
        return
    is_no_humans = "no_humans" in ctx.prompt
    if is_no_humans:
        logger.info("🏠 [Environment Pinning] Skipped for no_humans scene (Narrator)")
        return
    _apply_environment_pinning(req, args, ctx.warnings, db)


def _apply_ip_adapter(ctx: GenerationContext, strategy, args: list, db) -> None:
    """Apply IP-Adapter for style/identity transfer (strategy-driven)."""
    if not (strategy.ip_adapter_enabled and strategy.ip_adapter_reference):
        return
    ref_image = load_reference_image(strategy.ip_adapter_reference, db=db)
    if not ref_image:
        return
    try:
        args.append(
            build_ip_adapter_args(
                reference_image=ref_image,
                weight=strategy.ip_adapter_weight,
                model=strategy.ip_adapter_model,
                guidance_start=strategy.ip_adapter_guidance_start,
                guidance_end=strategy.ip_adapter_guidance_end,
            )
        )
        ctx.ip_adapter_used = strategy.ip_adapter_reference
        logger.info(
            "🧑 [IP-Adapter] Using reference: %s (weight=%.2f, guidance=%.2f~%.2f)",
            strategy.ip_adapter_reference,
            strategy.ip_adapter_weight,
            strategy.ip_adapter_guidance_start or 0.0,
            strategy.ip_adapter_guidance_end or 1.0,
        )
    except Exception as e:
        logger.warning("🧑 [IP-Adapter] Skipped - %s", str(e))


# ── Environment Pinning helpers (nesting 7→3) ────────────────────────


def _apply_environment_pinning(
    request: SceneGenerateRequest, controlnet_args_list: list, warnings: list[str], db
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

    _apply_canny_from_asset(env_asset, request, controlnet_args_list)


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
    """
    if env_asset.owner_type != "scene":
        return None

    from models.scene import Scene

    ref_scene = db.query(Scene).filter(Scene.id == env_asset.owner_id, Scene.deleted_at.is_(None)).first()
    if not ref_scene:
        return None

    tag_conflict = _check_tag_conflict(ref_scene, request, db)
    if tag_conflict:
        return tag_conflict

    return _check_keyword_conflict(ref_scene, request)


def _check_tag_conflict(ref_scene, request: SceneGenerateRequest, db) -> str | None:
    """Check environment tag mismatch between reference and current scene."""
    from services.prompt.v3_composition import LAYER_ENVIRONMENT, V3PromptBuilder

    ref_env = set(ref_scene.context_tags.get("environment", [])) if ref_scene.context_tags else set()
    if not ref_env:
        return None

    builder = V3PromptBuilder(db)
    curr_tokens = split_prompt_tokens(request.prompt)
    curr_tag_info = builder.get_tag_info(curr_tokens)
    curr_env = {tag for tag, info in curr_tag_info.items() if info.get("layer") == LAYER_ENVIRONMENT}

    if curr_env and not (ref_env & curr_env):
        return f"Location mismatch: {list(ref_env)} vs {list(curr_env)}"
    return None


def _check_keyword_conflict(ref_scene, request: SceneGenerateRequest) -> str | None:
    """Check location keyword mismatch between reference and current scene."""
    from config import LOCATION_KEYWORDS

    loc_kws = LOCATION_KEYWORDS
    ref_p = (ref_scene.image_prompt or "").lower()
    curr_p = request.prompt.lower()

    for kw in loc_kws:
        if kw in ref_p and any(other for other in loc_kws if other != kw and other in curr_p):
            return f"Keyword mismatch: Detected '{kw}' in reference but location changed in prompt"
    return None


def _apply_canny_from_asset(env_asset, request: SceneGenerateRequest, controlnet_args_list: list) -> None:
    """Apply Canny ControlNet from environment asset image."""
    import base64
    import os

    if not os.path.exists(env_asset.local_path):
        return

    try:
        with open(env_asset.local_path, "rb") as f:
            env_base64 = base64.b64encode(f.read()).decode("utf-8")
        controlnet_args_list.append(
            build_controlnet_args(
                input_image=env_base64,
                model="canny",
                weight=request.environment_reference_weight,
                control_mode="My prompt is more important",
            )
        )
        logger.info(
            "🏠 [Environment Pinning] Enabled using asset %d (weight=%.2f)",
            request.environment_reference_id,
            request.environment_reference_weight,
        )
    except Exception as e:
        logger.error("❌ [Environment Pinning] Failed to load asset: %s", e)


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
                Tag.category == "pose",
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
