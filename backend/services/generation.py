from __future__ import annotations

import httpx
from fastapi import HTTPException

from config import SD_TIMEOUT_SECONDS, SD_TXT2IMG_URL, logger
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
    extract_lora_names,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)


async def generate_scene_image(request: SceneGenerateRequest) -> dict:
    """Generate a scene image using Stable Diffusion."""
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    cleaned_prompt = normalize_prompt_tokens(request.prompt)

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
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
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
            ref_image = load_reference_image(request.ip_adapter_reference)
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
            return {"image": img, "controlnet_pose": controlnet_used, "ip_adapter_reference": ip_adapter_used}
    except httpx.HTTPError as exc:
        logger.exception("Scene generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
