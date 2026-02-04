from __future__ import annotations

import json
from contextlib import contextmanager

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from config import SD_TIMEOUT_SECONDS, SD_TXT2IMG_URL, logger
from database import SessionLocal
from schemas import SceneGenerateRequest
from services.controlnet import (
    build_controlnet_args,
    build_ip_adapter_args,
    check_controlnet_available,
    detect_pose_from_prompt,
    load_pose_reference,
    load_reference_image,
)
from services.lora_calibration import get_optimal_weights_from_db
from services.prompt import (
    apply_optimal_lora_weights,
    detect_scene_complexity,
    extract_lora_names,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)
from services.prompt.v3_service import V3PromptService


@contextmanager
def get_db_session():
    """Context manager for safe DB session lifecycle.

    Ensures session.close() is always called, preventing leaks
    that occurred with the old next(get_db()) pattern.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_style_profile_to_prompt(prompt: str, negative_prompt: str, storyboard_id: int | None, db) -> tuple[str, str]:
    """
    Apply Style Profile settings from Storyboard to prompt.

    Returns: (modified_prompt, modified_negative_prompt)
    """
    if not storyboard_id:
        return prompt, negative_prompt

    try:
        from models import LoRA, Storyboard, StyleProfile
        from models.group import Group
        from services.config_resolver import resolve_effective_config

        # Get storyboard, then resolve style_profile_id via cascade
        storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if not storyboard:
            return prompt, negative_prompt

        group = (
            db.query(Group)
            .options(
                joinedload(Group.config),
                joinedload(Group.project),
            )
            .filter(Group.id == storyboard.group_id)
            .first()
        )
        if not group:
            return prompt, negative_prompt

        cfg = resolve_effective_config(group.project, group)
        style_profile_id = cfg["values"].get("style_profile_id")
        if not style_profile_id:
            return prompt, negative_prompt

        # Get style profile
        profile = db.query(StyleProfile).filter(StyleProfile.id == style_profile_id).first()
        if not profile:
            return prompt, negative_prompt

        logger.info("🎨 [Style Profile] Applying '%s' (ID: %d)", profile.name, profile.id)

        # Build LoRA tags and trigger words
        lora_tags = []
        trigger_words = []

        if profile.loras:
            for lora_config in profile.loras:
                lora_id = lora_config.get("lora_id")
                lora_name = lora_config.get("name")
                weight = lora_config.get("weight", 0.7)

                # Get trigger words from LoRA model
                if lora_id:
                    lora_obj = db.query(LoRA).filter(LoRA.id == lora_id).first()
                    if lora_obj and lora_obj.trigger_words:
                        trigger_words.extend(lora_obj.trigger_words)

                # Add LoRA tag
                if lora_name:
                    lora_tags.append(f"<lora:{lora_name}:{weight}>")

        # Compose final prompt
        parts = []

        # 1. Default positive prompt (quality tags)
        if profile.default_positive:
            parts.append(profile.default_positive.strip())

        # 2. Trigger words
        if trigger_words:
            parts.append(", ".join(trigger_words))

        # 3. Original prompt
        if prompt:
            parts.append(prompt.strip())

        # 4. LoRA tags (at the end)
        if lora_tags:
            parts.append(", ".join(lora_tags))

        modified_prompt = ", ".join(parts)

        # Compose final negative prompt
        modified_negative = negative_prompt or ""
        if profile.default_negative:
            if modified_negative:
                modified_negative = f"{modified_negative}, {profile.default_negative}"
            else:
                modified_negative = profile.default_negative

        logger.info("✅ [Style Profile] Applied %d LoRAs, %d trigger words", len(lora_tags), len(trigger_words))
        logger.info("📝 [Style Profile] Final prompt: %s", modified_prompt[:200])

        return modified_prompt, modified_negative

    except Exception as e:
        logger.error(f"❌ [Style Profile] Error applying profile: {e}")
        return prompt, negative_prompt


async def generate_scene_image(request: SceneGenerateRequest) -> dict:
    """Generate a scene image using Stable Diffusion."""
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    with get_db_session() as db:
        return await _generate_scene_image_with_db(request, db)


def _prepare_prompt(request: SceneGenerateRequest, db) -> tuple[str, list[str], object]:
    """Prepare the final prompt via style profile + V3 composition.

    Returns: (cleaned_prompt, final_warnings, character_obj)
    """
    request.prompt, request.negative_prompt = apply_style_profile_to_prompt(
        request.prompt, request.negative_prompt or "", request.storyboard_id, db
    )

    from models import Character

    character_obj = db.query(Character).filter(Character.id == request.character_id).first()

    prompt_already_composed = "BREAK" in request.prompt or "masterpiece" in request.prompt.lower()
    if prompt_already_composed:
        cleaned_prompt = request.prompt
        logger.info("🎨 [V3 Engine] Using pre-composed prompt for character %d", request.character_id)
    else:
        v3_service = V3PromptService(db)
        scene_tags = split_prompt_tokens(request.prompt)
        cleaned_prompt = v3_service.generate_prompt_for_scene(
            character_id=request.character_id, scene_tags=scene_tags, style_loras=request.style_loras
        )
        logger.info("🎨 [V3 Engine] Composed prompt for character %d", request.character_id)

    final_warnings: list[str] = []

    # Character Consistency: Auto-apply IP-Adapter if reference exists
    if character_obj and not request.use_ip_adapter:
        ref_image_test = load_reference_image(character_obj.name, db=db)
        if ref_image_test:
            request.use_ip_adapter = True
            request.ip_adapter_reference = character_obj.name
            if character_obj.ip_adapter_weight:
                request.ip_adapter_weight = character_obj.ip_adapter_weight
            else:
                request.ip_adapter_weight = 0.35
                logger.info(
                    "✨ [Auto IP-Adapter] Enabled for character '%s' (weight=%.2f)",
                    character_obj.name,
                    request.ip_adapter_weight,
                )
    elif not character_obj:
        # Auto-populate character_id from IP-Adapter reference
        if request.use_ip_adapter and request.ip_adapter_reference:
            from models import Character

            character_obj = db.query(Character).filter(Character.name == request.ip_adapter_reference).first()
            if character_obj:
                request.character_id = character_obj.id
                logger.info(
                    "📊 [Activity Log] Auto-set character_id=%d from IP-Adapter reference '%s'",
                    request.character_id,
                    request.ip_adapter_reference,
                )
                v3_service = V3PromptService(db)
                scene_tags = split_prompt_tokens(request.prompt)
                cleaned_prompt = v3_service.generate_prompt_for_scene(
                    character_id=request.character_id,
                    scene_tags=scene_tags,
                    style_loras=request.style_loras,
                )
                logger.info("🎨 [V3 Engine] Composed prompt for auto-populated character %d", request.character_id)
        if not request.character_id:
            cleaned_prompt = normalize_prompt_tokens(request.prompt)

    return cleaned_prompt, final_warnings, character_obj


def _adjust_parameters(cleaned_prompt: str, request: SceneGenerateRequest, character_obj) -> tuple[str, int, float]:
    """Detect complexity, calibrate LoRA weights, adjust steps/cfg.

    Returns: (calibrated_prompt, final_steps, final_cfg)
    """
    tokens = split_prompt_tokens(cleaned_prompt)
    complexity = detect_scene_complexity(tokens)

    final_steps = request.steps
    final_cfg = request.cfg_scale

    if complexity == "complex":
        final_steps = max(final_steps, 28)
        logger.info(f"⚡ [Complexity] Boosted steps for complex scene: steps={final_steps}")
    elif complexity == "moderate":
        final_steps = max(final_steps, 25)

    # Apply optimal LoRA weights from calibration DB
    IP_ADAPTER_LORA_CAP = 0.6
    lora_names = extract_lora_names(cleaned_prompt)
    if lora_names:
        try:
            optimal_weights = get_optimal_weights_from_db(lora_names)
            if request.use_ip_adapter and character_obj and optimal_weights:
                optimal_weights = {name: min(w, IP_ADAPTER_LORA_CAP) for name, w in optimal_weights.items()}
                logger.info("🔧 [LoRA] IP-Adapter active, capped at %.1f: %s", IP_ADAPTER_LORA_CAP, optimal_weights)
            if optimal_weights:
                cleaned_prompt = apply_optimal_lora_weights(cleaned_prompt, optimal_weights)
                logger.info("🔧 [LoRA] Applied calibrated weights: %s", optimal_weights)
        except Exception as e:
            logger.warning("🔧 [LoRA] Failed to get optimal weights: %s", e)

    return cleaned_prompt, final_steps, final_cfg


def _build_payload(prompt: str, request: SceneGenerateRequest, steps: int, cfg: float) -> dict:
    """Build the SD txt2img payload."""
    cleaned_negative = normalize_negative_prompt(request.negative_prompt or "")
    payload = {
        "prompt": prompt,
        "negative_prompt": cleaned_negative,
        "steps": steps,
        "cfg_scale": cfg,
        "sampler_name": request.sampler_name,
        "seed": request.seed,
        "width": request.width,
        "height": request.height,
        "override_settings": {
            "CLIP_stop_at_last_layers": max(1, int(request.clip_skip)),
        },
        "override_settings_restore_afterwards": True,
        "batch_size": 1,
    }
    if request.enable_hr:
        payload.update(
            {
                "enable_hr": True,
                "hr_scale": request.hr_scale,
                "hr_upscaler": request.hr_upscaler,
                "hr_second_pass_steps": request.hr_second_pass_steps,
                "denoising_strength": request.denoising_strength,
            }
        )
    return payload


def _apply_controlnet(
    request: SceneGenerateRequest, payload: dict, character_obj, final_warnings: list[str], db
) -> tuple[str | None, str | None]:
    """Apply ControlNet + IP-Adapter to payload. Returns (controlnet_used, ip_adapter_used)."""
    controlnet_used = None
    ip_adapter_used = None
    controlnet_args_list = []

    if not check_controlnet_available():
        return controlnet_used, ip_adapter_used

    # ControlNet pose control
    if request.use_controlnet:
        pose_name = request.controlnet_pose
        if not pose_name:
            prompt_tags = split_prompt_tokens(request.prompt)
            pose_name = detect_pose_from_prompt(prompt_tags)

        if pose_name:
            pose_image = load_pose_reference(pose_name)
            if pose_image:
                controlnet_args_list.append(
                    build_controlnet_args(
                        input_image=pose_image,
                        model="openpose",
                        weight=request.controlnet_weight,
                        control_mode="Balanced",
                    )
                )
                controlnet_used = pose_name
                logger.info("🎭 [ControlNet] Using pose: %s (weight=%.1f)", pose_name, request.controlnet_weight)

    # Reference-only for Character Consistency
    if request.character_id and request.use_reference_only:
        ref_image = load_reference_image(character_obj.name if character_obj else request.ip_adapter_reference, db=db)
        if ref_image:
            controlnet_args_list.append(
                build_controlnet_args(
                    input_image=ref_image,
                    model="reference",
                    weight=request.reference_only_weight,
                    control_mode="Balanced",
                )
            )
            logger.info(
                "🎨 [Reference-only] Enabled for character consistency (weight=%.2f)", request.reference_only_weight
            )

    # Environment Pinning for Background Consistency
    if request.environment_reference_id:
        _apply_environment_pinning(request, controlnet_args_list, final_warnings, db)

    # IP-Adapter for Style/Identity Transfer
    if request.use_ip_adapter and request.ip_adapter_reference:
        ref_image = load_reference_image(request.ip_adapter_reference, db=db)
        if ref_image:
            try:
                controlnet_args_list.append(
                    build_ip_adapter_args(
                        reference_image=ref_image,
                        weight=request.ip_adapter_weight,
                        model=character_obj.ip_adapter_model if character_obj else None,
                    )
                )
                ip_adapter_used = request.ip_adapter_reference
                logger.info(
                    "🧑 [IP-Adapter] Using reference: %s (weight=%.1f)",
                    request.ip_adapter_reference,
                    request.ip_adapter_weight,
                )
            except Exception as e:
                logger.warning("🧑 [IP-Adapter] Skipped - %s", str(e))

    # Apply combined ControlNet args
    if controlnet_args_list:
        payload["alwayson_scripts"] = {"controlnet": {"args": controlnet_args_list}}
        for i, arg in enumerate(controlnet_args_list):
            debug_arg = {
                k: (v[:50] + "..." if k == "image" and isinstance(v, str) and len(v) > 50 else v)
                for k, v in arg.items()
            }
            logger.info("🔧 [ControlNet Arg %d] %s", i, debug_arg)

    return controlnet_used, ip_adapter_used


def _apply_environment_pinning(
    request: SceneGenerateRequest, controlnet_args_list: list, final_warnings: list[str], db
) -> None:
    """Handle environment reference pinning with conflict detection."""
    import base64

    from models.media_asset import MediaAsset
    from models.scene import Scene
    from services.prompt.v3_composition import LAYER_ENVIRONMENT, V3PromptBuilder

    env_asset = db.query(MediaAsset).filter(MediaAsset.id == request.environment_reference_id).first()
    if not env_asset or not env_asset.local_path:
        return

    try:
        is_conflict = False
        reason = ""

        if env_asset.owner_type == "scene":
            ref_scene = db.query(Scene).filter(Scene.id == env_asset.owner_id).first()
            if ref_scene:
                ref_env = set(ref_scene.context_tags.get("environment", [])) if ref_scene.context_tags else set()

                builder = V3PromptBuilder(db)
                curr_tokens = split_prompt_tokens(request.prompt)
                curr_tag_info = builder.get_tag_info(curr_tokens)
                curr_env = {tag for tag, info in curr_tag_info.items() if info.get("layer") == LAYER_ENVIRONMENT}

                if ref_env and curr_env and not (ref_env & curr_env):
                    is_conflict = True
                    reason = f"Location mismatch: {list(ref_env)} vs {list(curr_env)}"

                if not is_conflict:
                    loc_kws = ["kitchen", "beach", "forest", "room", "office", "street", "indoors", "outdoors"]
                    ref_p = (ref_scene.image_prompt or "").lower()
                    curr_p = request.prompt.lower()
                    for kw in loc_kws:
                        if kw in ref_p and any(other for other in loc_kws if other != kw and other in curr_p):
                            is_conflict = True
                            reason = f"Keyword mismatch: Detected '{kw}' in reference but location changed in prompt"
                            break

        if is_conflict:
            msg = f"장소 변화가 감지되어 배경 고정이 자동으로 해제되었습니다. ({reason})"
            logger.warning("⚠️ [Environment Pinning] %s", msg)
            final_warnings.append(msg)
        else:
            import os

            if os.path.exists(env_asset.local_path):
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
        logger.error("❌ [Environment Pinning] Failed to load or check asset: %s", e)


async def _call_sd_api(payload: dict, controlnet_used, ip_adapter_used, final_warnings) -> dict:
    """Call the SD txt2img API and parse the response."""
    logger.info("🧾 [Scene Gen Payload] %s", {k: v for k, v in payload.items() if k != "alwayson_scripts"})

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=SD_TIMEOUT_SECONDS)
            res.raise_for_status()
            data = res.json()
            raw_images = data.get("images", [])
            if not raw_images:
                raise HTTPException(status_code=500, detail="No images returned")

            # SD WebUI appends ControlNet preprocessor outputs after generated images.
            # With batch_size=1, only images[0] is the actual generation.
            batch_size = payload.get("batch_size", 1)
            images = raw_images[:batch_size]
            img = images[0]

            if request_seed_is_random(data):
                _try_parse_seed(data)

            return {
                "image": img,
                "images": images,
                "controlnet_pose": controlnet_used,
                "ip_adapter_reference": ip_adapter_used,
                "warnings": final_warnings,
            }
    except httpx.HTTPError as exc:
        logger.exception("Scene generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def request_seed_is_random(data: dict) -> bool:
    """Check if we should try to parse seed from response."""
    return "info" in data


def _try_parse_seed(data: dict) -> None:
    """Attempt to parse seed from SD response info (best-effort)."""
    try:
        info_val = data["info"]
        if isinstance(info_val, str):
            json.loads(info_val)
        elif isinstance(info_val, dict):
            pass
    except Exception:
        logger.warning("Failed to parse info from SD response", exc_info=True)


async def _generate_scene_image_with_db(request: SceneGenerateRequest, db) -> dict:
    """Internal generation logic with an externally managed DB session."""
    try:
        cleaned_prompt, final_warnings, character_obj = _prepare_prompt(request, db)
    except Exception as e:
        logger.error(f"Error during prompt preparation: {e}")
        cleaned_prompt = normalize_prompt_tokens(request.prompt)
        final_warnings = []
        character_obj = None

    cleaned_prompt, final_steps, final_cfg = _adjust_parameters(cleaned_prompt, request, character_obj)

    payload = _build_payload(cleaned_prompt, request, final_steps, final_cfg)

    controlnet_used, ip_adapter_used = _apply_controlnet(request, payload, character_obj, final_warnings, db)

    return await _call_sd_api(payload, controlnet_used, ip_adapter_used, final_warnings)
