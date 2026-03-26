"""Scene image generation pipeline.

Orchestrates: prompt preparation → parameter adjustment → payload build → SD API call.
Prompt logic is in generation_prompt.py, ControlNet in generation_controlnet.py,
Style Profile in generation_style.py.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING

import httpx
from fastapi import HTTPException

from config import (
    apply_sampler_to_payload,
    logger,
)
from database import SessionLocal
from schemas import SceneGenerateRequest
from services.generation_controlnet import apply_controlnet as _apply_controlnet
from services.generation_prompt import (
    _resolve_effective_character_b_id as _resolve_effective_character_b_id,  # noqa: F401, PLC0414
)
from services.generation_prompt import _resolve_style_loras as _resolve_style_loras  # noqa: F401, PLC0414
from services.generation_prompt import prepare_prompt as _prepare_prompt
from services.generation_style import apply_style_profile_to_prompt  # noqa: F401 — re-export for patch compat
from services.prompt import (
    detect_scene_complexity,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)
from services.sd_client.factory import get_sd_client

if TYPE_CHECKING:
    from services.generation_context import GenerationContext


@contextmanager
def get_db_session():
    """Context manager for safe DB session lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def generate_scene_image(request: SceneGenerateRequest) -> dict:
    """Generate a scene image using Stable Diffusion."""
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    with get_db_session() as db:
        return await _generate_scene_image_with_db(request, db)


# ── Pipeline stages ─────────────────────────────────────────────────


def _adjust_parameters(ctx: GenerationContext) -> None:
    """Detect complexity, adjust steps/cfg.

    Reads ctx.prompt, ctx.request, ctx.style_context.
    Writes ctx.prompt, ctx.steps, ctx.cfg_scale.

    Priority: StyleProfile defaults > request defaults, then complexity boost.
    """
    tokens = split_prompt_tokens(ctx.prompt)
    complexity = detect_scene_complexity(tokens)

    # Start from request defaults
    ctx.steps = ctx.request.steps
    ctx.cfg_scale = ctx.request.cfg_scale

    # Override with StyleProfile generation parameters if available
    style_ctx = ctx.style_context
    if style_ctx:
        if style_ctx.default_steps is not None:
            ctx.steps = style_ctx.default_steps
        if style_ctx.default_cfg_scale is not None:
            ctx.cfg_scale = style_ctx.default_cfg_scale
        if style_ctx.default_sampler_name:
            ctx.request.sampler_name = style_ctx.default_sampler_name
        if style_ctx.default_clip_skip is not None:
            ctx.request.clip_skip = style_ctx.default_clip_skip
        logger.info(
            "🎨 [StyleProfile] Applied params: steps=%d, cfg=%.1f, sampler=%s, clip_skip=%d",
            ctx.steps,
            ctx.cfg_scale,
            ctx.request.sampler_name,
            ctx.request.clip_skip,
        )

    # Complexity boost: only when steps weren't explicitly overridden
    # (StyleProfile set explicit steps, or caller set non-default steps)
    from config import SD_DEFAULT_STEPS

    has_explicit_steps = (style_ctx and style_ctx.default_steps is not None) or (ctx.request.steps != SD_DEFAULT_STEPS)
    if not has_explicit_steps:
        if complexity == "complex":
            ctx.steps = max(ctx.steps, 28)
            logger.info("⚡ [Complexity] Boosted steps for complex scene: steps=%d", ctx.steps)
        elif complexity == "moderate":
            ctx.steps = max(ctx.steps, 25)


def _build_payload(ctx: GenerationContext) -> dict:
    """Build the SD txt2img payload from context."""
    req = ctx.request
    cleaned_negative = normalize_negative_prompt(ctx.negative_prompt)
    payload = {
        "prompt": ctx.prompt,
        "negative_prompt": cleaned_negative,
        "steps": ctx.steps,
        "cfg_scale": ctx.cfg_scale,
        "seed": req.seed,
        "width": req.width,
        "height": req.height,
        "clip_skip": max(1, int(req.clip_skip)),
        "batch_size": 1,
        "_comfy_workflow": req.comfy_workflow or "scene_single",
    }
    if ctx.style_context and ctx.style_context.sd_model_name:
        payload["sd_model_checkpoint"] = ctx.style_context.sd_model_name
    apply_sampler_to_payload(payload, req.sampler_name)
    return payload


async def _call_sd_api(payload: dict, ctx: GenerationContext) -> dict:
    """Call the SD txt2img API with cache support.

    Delegates to cache layer for deterministic seeds, then to raw API call.
    """
    from services.image_cache import get_cached_image, image_cache_key, save_cached_image

    is_deterministic = payload.get("seed", -1) != -1
    cache_key = image_cache_key(payload) if is_deterministic else None

    # Cache check (only for deterministic seeds)
    if cache_key:
        cached = get_cached_image(cache_key)
        if cached is not None:
            return {
                "image": cached,
                "images": [cached],
                "seed": payload["seed"],
                "controlnet_pose": ctx.controlnet_used,
                "ip_adapter_reference": ctx.ip_adapter_used,
                "warnings": [*ctx.warnings, "cache_hit"],
            }

    result = await _call_sd_api_raw(payload, ctx)

    # Save to cache (deterministic only)
    if cache_key and result.get("image"):
        save_cached_image(cache_key, result["image"])

    return result


async def _call_sd_api_raw(payload: dict, ctx: GenerationContext) -> dict:
    """Send request to SD txt2img API and parse the response."""
    logger.info("🧾 [Scene Gen Payload] %s", {k: v for k, v in payload.items() if k != "alwayson_scripts"})

    try:
        result = await get_sd_client().txt2img(payload)
        if not result.images:
            raise HTTPException(status_code=500, detail="No images returned")

        batch_size = payload.get("batch_size", 1)
        images = result.images[:batch_size]

        return {
            "image": images[0],
            "images": images,
            "seed": result.seed,
            "controlnet_pose": ctx.controlnet_used,
            "ip_adapter_reference": ctx.ip_adapter_used,
            "warnings": ctx.warnings,
        }
    except httpx.HTTPError as exc:
        from services.error_responses import raise_user_error

        raise_user_error("image_generate", exc, status_code=502)
        raise  # unreachable; satisfies type checker


def _has_info(data: dict) -> bool:
    """Check if SD response contains info for seed parsing."""
    return "info" in data


def _try_parse_seed(data: dict) -> int | None:
    """Parse actual seed from SD response info. Returns seed or None."""
    try:
        info_val = data["info"]
        info_dict = json.loads(info_val) if isinstance(info_val, str) else info_val
        if isinstance(info_dict, dict):
            seed = info_dict.get("seed")
            if seed is not None:
                return int(seed)
    except Exception:
        logger.debug("Failed to parse seed from SD response", exc_info=True)
    return None


# ── Main pipeline ───────────────────────────────────────────────────


async def _generate_scene_image_with_db(request: SceneGenerateRequest, db) -> dict:
    """Internal generation logic with an externally managed DB session.

    Pipeline stages:
    1. Seed anchoring   → resolve deterministic seed
    2. _prepare_prompt   → ctx.prompt, ctx.negative_prompt, ctx.warnings
    3. _adjust_parameters → ctx.prompt (calibrated), ctx.steps, ctx.cfg_scale
    4. _build_payload    → SD API payload dict
    5. _apply_controlnet → ctx.controlnet_used, ctx.ip_adapter_used
    6. _call_sd_api      → final result
    """
    from models.scene import Scene
    from services.generation_context import GenerationContext
    from services.seed_anchoring import resolve_scene_seed

    ctx = GenerationContext(request=request)

    # Resolve seed via anchoring (before prompt/payload)
    scene_obj = None
    scene_order = 0
    if request.scene_id:
        scene_obj = db.query(Scene).filter(Scene.id == request.scene_id, Scene.deleted_at.is_(None)).first()
        if scene_obj:
            scene_order = scene_obj.order or 0

    resolved_seed = resolve_scene_seed(request.seed, request.storyboard_id, scene_order, db)
    if resolved_seed != request.seed:
        request.seed = resolved_seed

    try:
        _prepare_prompt(request, db, ctx)
    except Exception as e:
        logger.error("Error during prompt preparation: %s", e)
        ctx.prompt = normalize_prompt_tokens(request.prompt)

    _adjust_parameters(ctx)

    payload = _build_payload(ctx)

    _apply_controlnet(payload, ctx, db)

    result = await _call_sd_api(payload, ctx)
    result["used_prompt"] = ctx.prompt
    result["used_negative_prompt"] = ctx.negative_prompt
    result["used_steps"] = ctx.steps
    result["used_cfg_scale"] = ctx.cfg_scale
    result["used_sampler"] = ctx.request.sampler_name
    result["consistency_quality"] = ctx.consistency.quality_score

    if ctx.consistency.quality_score == "low":
        low_msg = "캐릭터 일관성 품질이 낮습니다 (LoRA/레퍼런스 부족). 캐릭터 설정을 확인하세요."
        result.setdefault("warnings", []).append(low_msg)
        logger.warning("[Generation] Consistency quality=low for character — %s", low_msg)

    return result
