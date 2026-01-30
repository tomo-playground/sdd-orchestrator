from __future__ import annotations

import json

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


async def generate_scene_image(request: SceneGenerateRequest) -> dict:
    """Generate a scene image using Stable Diffusion."""
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    db = SessionLocal()
    try:
        # V3 Logic: If character_id is provided, use V3PromptService
        if request.character_id:
            v3_service = V3PromptService(db)
            # Treat request.prompt as scene tags (comma-separated)
            scene_tags = split_prompt_tokens(request.prompt)
            cleaned_prompt = v3_service.generate_prompt_for_scene(
                character_id=request.character_id,
                scene_tags=scene_tags
            )
            logger.info("🎨 [V3 Engine] Composed prompt for character %d", request.character_id)
        else:
            cleaned_prompt = normalize_prompt_tokens(request.prompt)
    except Exception as e:
        logger.error(f"Error during prompt preparation: {e}")
        cleaned_prompt = normalize_prompt_tokens(request.prompt)
    # We keep db open for later IP-adapter use

    # Detect complexity and adjust parameters
    tokens = split_prompt_tokens(cleaned_prompt)
    complexity = detect_scene_complexity(tokens)

    final_steps = request.steps
    final_cfg = request.cfg_scale

    if complexity == "complex":
        final_steps = max(final_steps, 28)
        final_cfg = max(final_cfg, 8.0)
        logger.info(f"⚡ [Complexity] Boosted parameters for complex scene: steps={final_steps}, cfg={final_cfg}")
    elif complexity == "moderate":
        final_steps = max(final_steps, 25)
        # Keep CFG as is or slight boost
        final_cfg = max(final_cfg, 7.5)

    # Apply optimal LoRA weights from calibration DB
    lora_names = extract_lora_names(cleaned_prompt)
    if lora_names:
        try:
            optimal_weights = get_optimal_weights_from_db(lora_names)
            if optimal_weights:
                cleaned_prompt = apply_optimal_lora_weights(cleaned_prompt, optimal_weights)
                logger.info("🔧 [LoRA] Applied calibrated weights: %s", optimal_weights)
        except Exception as e:
            logger.warning("🔧 [LoRA] Failed to get optimal weights: %s", e)

    cleaned_negative = normalize_negative_prompt(request.negative_prompt or "")
    payload = {
        "prompt": cleaned_prompt,
        "negative_prompt": cleaned_negative,
        "steps": final_steps,
        "cfg_scale": final_cfg,
        "sampler_name": request.sampler_name,
        "seed": request.seed,
        "width": request.width,
        "height": request.height,
        "override_settings": {
            "CLIP_stop_at_last_layers": max(1, int(request.clip_skip)),
        },
        "override_settings_restore_afterwards": True,
    }
    if request.enable_hr:
        payload.update({
            "enable_hr": True,
            "hr_scale": request.hr_scale,
            "hr_upscaler": request.hr_upscaler,
            "hr_second_pass_steps": request.hr_second_pass_steps,
            "denoising_strength": request.denoising_strength,
        })

    # ControlNet + IP-Adapter integration
    controlnet_used = None
    ip_adapter_used = None
    controlnet_args_list = []

    if check_controlnet_available():
        # ControlNet pose control
        if request.use_controlnet:
            pose_name = request.controlnet_pose
            if not pose_name:
                prompt_tags = split_prompt_tokens(request.prompt)
                pose_name = detect_pose_from_prompt(prompt_tags)

            if pose_name:
                pose_image = load_pose_reference(pose_name)
                if pose_image:
                    controlnet_args_list.append(build_controlnet_args(
                        input_image=pose_image,
                        model="openpose",
                        weight=request.controlnet_weight,
                    ))
                    controlnet_used = pose_name
                    logger.info("🎭 [ControlNet] Using pose: %s (weight=%.1f)", pose_name, request.controlnet_weight)

        # IP-Adapter character consistency
        if request.use_ip_adapter and request.ip_adapter_reference:
            ref_image = load_reference_image(request.ip_adapter_reference, db=db)
            if ref_image:
                try:
                    controlnet_args_list.append(build_ip_adapter_args(
                        reference_image=ref_image,
                        weight=request.ip_adapter_weight,
                    ))
                    ip_adapter_used = request.ip_adapter_reference
                    logger.info("🧑 [IP-Adapter] Using reference: %s (weight=%.1f)", request.ip_adapter_reference, request.ip_adapter_weight)
                except Exception as e:
                    logger.warning("🧑 [IP-Adapter] Skipped - %s", str(e))

        # Apply combined ControlNet args
        if controlnet_args_list:
            payload["alwayson_scripts"] = {
                "controlnet": {"args": controlnet_args_list}
            }
            # Debug: log controlnet config (without base64 image)
            for i, arg in enumerate(controlnet_args_list):
                debug_arg = {k: (v[:50] + "..." if k == "image" and isinstance(v, str) and len(v) > 50 else v) for k, v in arg.items()}
                logger.info("🔧 [ControlNet Arg %d] %s", i, debug_arg)

    logger.info("🧾 [Scene Gen Payload] %s", {k: v for k, v in payload.items() if k != "alwayson_scripts"})

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=SD_TIMEOUT_SECONDS)
            res.raise_for_status()
            data = res.json()
            img = data.get("images", [None])[0]
            if not img:
                raise HTTPException(status_code=500, detail="No image returned")

            # Extract seed from response info
            actual_seed = None
            if request.seed != -1:
                actual_seed = request.seed
            elif "info" in data:
                try:
                    info_val = data["info"]
                    if isinstance(info_val, str):
                        info_data = json.loads(info_val)
                        actual_seed = info_data.get("seed")
                    elif isinstance(info_val, dict):
                        actual_seed = info_val.get("seed")
                except Exception:
                    logger.warning("Failed to parse info from SD response", exc_info=True)

            # Save generation log for analytics
            _save_generation_log(
                request=request,
                prompt=cleaned_prompt,
                negative_prompt=cleaned_negative,
                tags=tokens,
                sd_params={
                    "steps": final_steps,
                    "cfg_scale": final_cfg,
                    "sampler": request.sampler_name,
                    "width": request.width,
                    "height": request.height,
                },
                seed=actual_seed,
            )

            return {"image": img, "controlnet_pose": controlnet_used, "ip_adapter_reference": ip_adapter_used}
    except httpx.HTTPError as exc:
        logger.exception("Scene generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        db.close()



def _save_generation_log(
    request: SceneGenerateRequest,
    prompt: str,
    negative_prompt: str,
    tags: list[str],
    sd_params: dict,
    seed: int | None,
) -> None:
    """Save generation log for analytics (non-blocking).

    Args:
        request: Original generation request
        prompt: Normalized prompt used for generation
        negative_prompt: Negative prompt used for generation
        tags: Extracted prompt tokens
        sd_params: SD parameters (steps, cfg_scale, sampler, etc.)
        seed: Actual seed used (or None)
    """
    try:

        from database import SessionLocal
        from models.activity_log import ActivityLog

        # Use storyboard_id from request
        storyboard_id = request.storyboard_id

        scene_index = request.scene_index if request.scene_index is not None else 0

        db = SessionLocal()
        try:
            log = ActivityLog(
                storyboard_id=storyboard_id,
                scene_id=scene_index,
                character_id=request.character_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                tags_used=tags,
                sd_params=sd_params,
                seed=seed,
                status="pending",  # Will be updated after validation
                match_rate=None,  # Will be calculated during validation
                image_url=None,  # Not available yet (base64 only)
            )
            db.add(log)
            db.commit()
            logger.info(
                "📊 [Analytics] Saved activity log: storyboard=%s, scene=%d, tags=%d%s",
                storyboard_id,
                scene_index,
                len(tags),
                f" (topic={request.topic})" if request.topic else "",
            )
        except Exception as e:
            db.rollback()
            logger.warning("📊 [Analytics] Failed to save activity log: %s", str(e))
        finally:
            db.close()
    except Exception as e:
        # Non-blocking: log warning but don't fail generation
        logger.warning("📊 [Analytics] Failed to import ActivityLog: %s", str(e))
