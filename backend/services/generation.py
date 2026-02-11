from __future__ import annotations

import json
import re
from contextlib import contextmanager

import httpx
from fastapi import HTTPException

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
from services.image_generation_core import compose_scene_with_style
from services.keywords.core import normalize_prompt_token
from services.lora_calibration import get_optimal_weights_from_db
from services.prompt import (
    apply_optimal_lora_weights,
    detect_scene_complexity,
    extract_lora_names,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)

_PERSON_INDICATORS = frozenset({"1girl", "1boy", "2girls", "2boys", "3girls", "3boys", "solo", "couple", "group"})


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



def apply_style_profile_to_prompt(
    prompt: str, negative_prompt: str, storyboard_id: int | None, db, *, skip_loras: bool = False
) -> tuple[str, str]:
    """
    Apply Style Profile settings from Storyboard to prompt.

    Returns: (modified_prompt, modified_negative_prompt)
    """
    if not storyboard_id:
        return prompt, negative_prompt

    try:
        from services.style_context import resolve_style_context

        ctx = resolve_style_context(storyboard_id, db)
        if not ctx:
            return prompt, negative_prompt

        logger.info("🎨 [Style Profile] Applying '%s' (ID: %d)", ctx.profile_name, ctx.profile_id)

        # Build LoRA tags and trigger words from StyleContext
        lora_tags = []
        trigger_words = []

        if ctx.loras and not skip_loras:
            for lr in ctx.loras:
                if lr.get("trigger_words"):
                    trigger_words.extend(lr["trigger_words"])
                lora_tags.append(f"<lora:{lr['name']}:{lr['weight']}>")

        pos_emb_triggers = ctx.positive_embeddings
        neg_emb_triggers = ctx.negative_embeddings

        # Compose final prompt — deduplicate default_positive against existing prompt
        existing_normalized = {
            normalize_prompt_token(t) for t in split_prompt_tokens(prompt) if normalize_prompt_token(t)
        }

        # Defense-in-depth: skip LoRA tags/trigger words already in prompt
        existing_lora_names = set(re.findall(r"<lora:([^:]+):", prompt))
        if existing_lora_names:
            lora_tags = [t for t in lora_tags if re.search(r"<lora:([^:]+):", t).group(1) not in existing_lora_names]
            trigger_words = [tw for tw in trigger_words if normalize_prompt_token(tw) not in existing_normalized]

        parts = []

        # 1. Default positive prompt (quality tags), skip tokens already in prompt
        if ctx.default_positive:
            new_tokens = [
                t
                for t in split_prompt_tokens(ctx.default_positive)
                if normalize_prompt_token(t) not in existing_normalized
            ]
            if new_tokens:
                parts.append(", ".join(new_tokens))

        # 2. Trigger words (deduplicated above)
        if trigger_words:
            parts.append(", ".join(trigger_words))

        # 3. Positive embedding triggers
        if pos_emb_triggers:
            parts.append(", ".join(pos_emb_triggers))

        # 4. Original prompt
        if prompt:
            parts.append(prompt.strip())

        # 5. LoRA tags (at the end)
        if lora_tags:
            parts.append(", ".join(lora_tags))

        modified_prompt = ", ".join(parts)

        # Compose final negative prompt
        modified_negative = negative_prompt or ""
        if neg_emb_triggers:
            emb_str = ", ".join(neg_emb_triggers)
            modified_negative = f"{emb_str}, {modified_negative}" if modified_negative else emb_str
        if ctx.default_negative:
            if modified_negative:
                modified_negative = f"{modified_negative}, {ctx.default_negative}"
            else:
                modified_negative = ctx.default_negative

        logger.info(
            "✅ [Style Profile] Applied %d LoRAs, %d trigger words, %d pos embeds, %d neg embeds",
            len(lora_tags),
            len(trigger_words),
            len(pos_emb_triggers),
            len(neg_emb_triggers),
        )
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


def _resolve_style_loras(storyboard_id: int | None, db) -> list[dict]:
    """Resolve style LoRAs from DB config cascade for V3 engine.

    Delegates to image_generation_core.resolve_style_loras_from_storyboard (SSOT).
    """
    if not storyboard_id:
        return []
    try:
        from services.image_generation_core import resolve_style_loras_from_storyboard

        return resolve_style_loras_from_storyboard(storyboard_id, db)
    except Exception as e:
        logger.error("❌ [_resolve_style_loras] Error: %s", e)
        return []


def _resolve_effective_character_b_id(request: SceneGenerateRequest, db) -> int | None:
    """Resolve character_b_id only when scene_mode='multi'.

    Frontend always passes character_b_id from store state (no logic).
    Backend decides usage based on scene_mode from DB.
    """
    if not request.character_b_id:
        return None
    if not request.scene_id:
        return None
    from models.scene import Scene

    scene = db.query(Scene).filter(Scene.id == request.scene_id).first()
    if scene and scene.scene_mode == "multi":
        logger.debug("👥 [Multi-Char] scene_mode=multi, using character_b_id=%d", request.character_b_id)
        return request.character_b_id
    return None


def _inject_narrator_defense(request: SceneGenerateRequest) -> None:
    """Auto-inject no_humans for background scenes without person indicators."""
    if request.character_id or request.prompt_pre_composed:
        return
    prompt_norm = request.prompt.lower().replace(" ", "_")
    has_person = any(ind in prompt_norm for ind in _PERSON_INDICATORS)
    if not has_person and "no_humans" not in prompt_norm:
        request.prompt = f"no_humans, {request.prompt}"
        logger.info("🚫 [Narrator] Auto-injected no_humans for background scene")


def _handle_pre_composed(request: SceneGenerateRequest, db) -> tuple[str, list[str]]:
    """Handle prompt_pre_composed=True: style profile + safety-net LoRA injection."""
    has_lora_tags = "<lora:" in request.prompt
    request.prompt, request.negative_prompt = apply_style_profile_to_prompt(
        request.prompt,
        request.negative_prompt or "",
        request.storyboard_id,
        db,
        skip_loras=has_lora_tags,
    )
    # Safety net: if still no LoRA tags, resolve from DB and append
    if "<lora:" not in request.prompt and request.storyboard_id:
        style_loras = _resolve_style_loras(request.storyboard_id, db)
        if style_loras:
            lora_parts = []
            for lr in style_loras:
                lora_parts.append(f"<lora:{lr['name']}:{lr['weight']}>")
                for tw in lr.get("trigger_words", []):
                    if tw.lower() not in request.prompt.lower():
                        lora_parts.append(tw)
            request.prompt = f"{request.prompt}, {', '.join(lora_parts)}"
            logger.info(
                "🔧 [V3 Engine] Injected missing style LoRAs into pre-composed prompt: %s",
                [lr["name"] for lr in style_loras],
            )
    logger.debug("🎨 [V3 Engine] Using pre-composed prompt (prompt_pre_composed=True)")
    return request.prompt, []


def _resolve_background(request: SceneGenerateRequest, db) -> tuple[list[str] | None, int | None, float | None]:
    """Resolve background tags and ControlNet reference from background_id.

    Returns: (background_tags, background_image_asset_id, background_weight)
    """
    if not request.background_id:
        return None, None, None
    from models.background import Background

    bg = db.query(Background).filter(Background.id == request.background_id).first()
    if not bg:
        logger.warning("⚠️ [Background] background_id=%d not found", request.background_id)
        return None, None, None

    bg_tags = bg.tags if bg.tags else None
    bg_image_asset_id = bg.image_asset_id
    bg_weight = bg.weight
    logger.info(
        "🏠 [Background] Loaded '%s': tags=%s, image_asset_id=%s, weight=%.2f",
        bg.name, bg_tags, bg_image_asset_id, bg_weight,
    )
    return bg_tags, bg_image_asset_id, bg_weight


def _handle_character_scene(
    request: SceneGenerateRequest, db, effective_b_id: int | None
) -> tuple[str, list[str]]:
    """Handle raw prompt + character: V3 composition with style LoRAs."""
    style_loras = _resolve_style_loras(request.storyboard_id, db)
    logger.debug("🎨 [V3 Engine] Path B: style_loras=%s (from DB)", [lr.get("name") for lr in style_loras])
    bg_tags, bg_image_asset_id, bg_weight = _resolve_background(request, db)
    cleaned_prompt, request.negative_prompt, compose_warnings = compose_scene_with_style(
        raw_prompt=request.prompt,
        negative_prompt=request.negative_prompt or "",
        character_id=request.character_id,
        storyboard_id=request.storyboard_id,
        style_loras=style_loras,
        db=db,
        scene_id=request.scene_id,
        character_b_id=effective_b_id,
        background_tags=bg_tags,
    )
    # Auto-set environment reference from background image
    if bg_image_asset_id and not request.environment_reference_id:
        request.environment_reference_id = bg_image_asset_id
        request.environment_reference_weight = bg_weight or 0.3
        logger.info("🏠 [Background] Auto-set environment_reference_id=%d (weight=%.2f)", bg_image_asset_id, bg_weight or 0.3)
    logger.debug("🎨 [V3 Engine] Composed prompt for character %d", request.character_id)
    return cleaned_prompt, compose_warnings


def _handle_background_scene(request: SceneGenerateRequest, db) -> tuple[str, list[str]]:
    """Handle narrator (no_humans) scene: V3 background composition."""
    style_loras = _resolve_style_loras(request.storyboard_id, db)
    # Narrator scenes: only inject tags, skip ControlNet Canny (no_humans skips env pinning in _apply_controlnet)
    bg_tags, _, _ = _resolve_background(request, db)
    cleaned_prompt, request.negative_prompt, compose_warnings = compose_scene_with_style(
        raw_prompt=request.prompt,
        negative_prompt=request.negative_prompt or "",
        character_id=None,
        storyboard_id=request.storyboard_id,
        style_loras=style_loras,
        db=db,
        scene_id=request.scene_id,
        background_tags=bg_tags,
    )
    logger.debug("🎨 [V3 Engine] Background scene composition for Narrator")
    return cleaned_prompt, compose_warnings


def _handle_fallback(request: SceneGenerateRequest, db) -> tuple[str, list[str]]:
    """Handle no character, no no_humans: full style profile, no V3."""
    request.prompt, request.negative_prompt = apply_style_profile_to_prompt(
        request.prompt, request.negative_prompt or "", request.storyboard_id, db
    )
    return request.prompt, []


def _dispatch_prompt_route(
    request: SceneGenerateRequest, db, character_obj, effective_b_id: int | None
) -> tuple[str, list[str]]:
    """Route to appropriate prompt handler based on request state."""
    if request.prompt_pre_composed:
        return _handle_pre_composed(request, db)
    elif request.character_id and character_obj:
        return _handle_character_scene(request, db, effective_b_id)
    elif "no_humans" in request.prompt.lower().replace(" ", "_"):
        return _handle_background_scene(request, db)
    else:
        return _handle_fallback(request, db)


def _handle_ip_adapter_auto(
    request: SceneGenerateRequest, db, cleaned_prompt: str,
    final_warnings: list[str], character_obj, effective_b_id: int | None,
) -> tuple[str, object]:
    """Auto-apply IP-Adapter and handle IP-Adapter reference character lookup."""
    from models import Character

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
        if request.use_ip_adapter and request.ip_adapter_reference:
            character_obj = db.query(Character).filter(Character.name == request.ip_adapter_reference).first()
            if character_obj:
                request.character_id = character_obj.id
                logger.info(
                    "📊 [Activity Log] Auto-set character_id=%d from IP-Adapter reference '%s'",
                    request.character_id,
                    request.ip_adapter_reference,
                )
                style_loras = _resolve_style_loras(request.storyboard_id, db)
                cleaned_prompt, request.negative_prompt, compose_warnings = compose_scene_with_style(
                    raw_prompt=request.prompt,
                    negative_prompt=request.negative_prompt or "",
                    character_id=request.character_id,
                    storyboard_id=request.storyboard_id,
                    style_loras=style_loras,
                    db=db,
                    scene_id=request.scene_id,
                    character_b_id=effective_b_id,
                )
                final_warnings.extend(compose_warnings)
                logger.info("🎨 [V3 Engine] Composed prompt for auto-populated character %d", request.character_id)
        if not request.character_id and "no_humans" not in request.prompt.lower().replace(" ", "_"):
            cleaned_prompt = normalize_prompt_tokens(request.prompt)

    return cleaned_prompt, character_obj


def _append_narrator_negative(request: SceneGenerateRequest) -> None:
    """Append person-exclusion tags to negative prompt for narrator scenes."""
    if "no_humans" not in request.prompt:
        return
    from config import NARRATOR_NEGATIVE_PROMPT_EXTRA

    request.negative_prompt = f"{request.negative_prompt}, {NARRATOR_NEGATIVE_PROMPT_EXTRA}"
    logger.info("🚫 [Narrator Negative] Appended person-exclusion tags to negative prompt")


def _prepare_prompt(request: SceneGenerateRequest, db) -> tuple[str, list[str], object]:
    """Orchestrator: prepare the final prompt via style profile + V3 composition.

    Routes to specialized handlers based on request state:
    - pre_composed: _handle_pre_composed
    - character scene: _handle_character_scene
    - background (no_humans): _handle_background_scene
    - fallback: _handle_fallback

    Returns: (cleaned_prompt, final_warnings, character_obj)
    """
    from models import Character

    character_obj = db.query(Character).filter(Character.id == request.character_id).first()
    effective_b_id = _resolve_effective_character_b_id(request, db)

    logger.debug(
        "🔀 [Prompt Route] pre_composed=%s, character_id=%s, character_found=%s",
        request.prompt_pre_composed,
        request.character_id,
        character_obj is not None,
    )

    _inject_narrator_defense(request)

    cleaned_prompt, final_warnings = _dispatch_prompt_route(
        request, db, character_obj, effective_b_id
    )

    # Debug: verify LoRA tags in final prompt
    lora_tags_found = re.findall(r"<lora:[^>]+>", cleaned_prompt)
    if lora_tags_found:
        logger.debug("✅ [LoRA Check] %d LoRA tags in prompt: %s", len(lora_tags_found), lora_tags_found)
    else:
        logger.warning("⚠️ [LoRA Check] No <lora:> tags found in cleaned prompt!")

    cleaned_prompt, character_obj = _handle_ip_adapter_auto(
        request, db, cleaned_prompt, final_warnings,
        character_obj, effective_b_id,
    )

    _append_narrator_negative(request)

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
    # V3 composition의 _cap_lora_weight()가 STYLE_LORA_WEIGHT_CAP SSOT.
    # 여기서는 calibration DB 기반 최적화만 수행 (이중 capping 제거).
    lora_names = extract_lora_names(cleaned_prompt)
    if lora_names:
        try:
            optimal_weights = get_optimal_weights_from_db(lora_names)
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
    # Skip for Narrator scenes (no_humans) — reference images containing characters
    # would inject character edges via Canny, defeating the no_humans intent
    is_no_humans = "no_humans" in request.prompt
    if request.environment_reference_id and not is_no_humans:
        _apply_environment_pinning(request, controlnet_args_list, final_warnings, db)
    elif request.environment_reference_id and is_no_humans:
        logger.info("🏠 [Environment Pinning] Skipped for no_humans scene (Narrator)")

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
            ref_scene = db.query(Scene).filter(Scene.id == env_asset.owner_id, Scene.deleted_at.is_(None)).first()
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

    result = await _call_sd_api(payload, controlnet_used, ip_adapter_used, final_warnings)
    result["used_prompt"] = cleaned_prompt
    return result
