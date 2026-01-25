"""Prompt manipulation endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

import logic
from config import logger, SD_LORAS_URL
from schemas import (
    PromptComposeRequest,
    PromptComposeResponse,
    PromptRewriteRequest,
    PromptSplitRequest,
    PromptValidateRequest,
)
from services.prompt import validate_loras, detect_prompt_conflicts, validate_identity_tags
from services.prompt_composition import (
    calculate_lora_weight,
    compose_prompt_tokens,
    detect_scene_complexity,
    get_effective_mode_from_dict,
)

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/rewrite")
async def rewrite_prompt(request: PromptRewriteRequest):
    logger.info("📥 [Prompt Rewrite Req] %s", request.model_dump())
    return logic.logic_rewrite_prompt(request)


@router.post("/split")
async def split_prompt(request: PromptSplitRequest):
    logger.info("📥 [Prompt Split Req] %s", request.model_dump())
    return logic.logic_split_prompt(request)


@router.post("/validate")
async def validate_prompt(request: PromptValidateRequest):
    """Validate prompt before image generation.

    Checks:
    1. LoRA existence in SD WebUI
    2. Positive-Negative prompt conflicts

    Returns validation result with warnings/errors.
    """
    logger.info("📥 [Prompt Validate] positive=%d chars, negative=%d chars",
                len(request.positive), len(request.negative))

    # Fetch available LoRAs from SD WebUI
    available_loras = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(SD_LORAS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, list):
                available_loras = [item.get("name", "") for item in data if item.get("name")]
    except httpx.HTTPError as exc:
        logger.warning("⚠️ [Prompt Validate] Failed to fetch LoRAs: %s", exc)
        # Continue validation without LoRA check

    # Validate LoRAs
    lora_result = validate_loras(request.positive, available_loras)

    # Detect conflicts
    conflict_result = detect_prompt_conflicts(request.positive, request.negative)

    # Validate identity tags
    identity_result = validate_identity_tags(request.positive)

    # Determine overall validity
    is_valid = (
        lora_result["valid"]
        and not conflict_result["has_conflicts"]
        and identity_result["valid"]
    )
    warnings = []
    errors = []

    if not lora_result["valid"]:
        errors.append(f"Missing LoRAs: {', '.join(lora_result['missing'])}")

    if conflict_result["has_conflicts"]:
        warnings.append(f"Conflicting tags in positive/negative: {', '.join(conflict_result['conflicts'])}")

    if not identity_result["valid"]:
        warnings.append(f"Missing identity tag: {identity_result['suggested']}")

    logger.info("✅ [Prompt Validate] valid=%s, loras=%s, conflicts=%s, identity=%s",
                is_valid, lora_result["prompt_loras"], conflict_result["conflicts"],
                identity_result["found_tags"])

    return {
        "valid": is_valid,
        "warnings": warnings,
        "errors": errors,
        "lora_validation": lora_result,
        "conflict_detection": conflict_result,
        "identity_validation": identity_result,
    }


@router.post("/compose", response_model=PromptComposeResponse)
async def compose_prompt(request: PromptComposeRequest):
    """Compose a prompt using Mode A/B logic.

    Mode A (Standard): No LoRA or style-only LoRA
      - Token order: Quality → Subject → Character → Appearance → Scene
      - Full appearance tags included

    Mode B (LoRA): Character LoRA present
      - Token order: Quality → Subject → Scene Core → LoRA → BREAK → Character
      - Scene tags prioritized, LoRA weight dynamically adjusted

    Returns the composed prompt with metadata including:
      - effective_mode: The actual mode used (standard or lora)
      - scene_complexity: simple, moderate, or complex
      - lora_weights: Calculated weights for each LoRA
    """
    logger.info(
        "📥 [Prompt Compose] tokens=%d, mode=%s, loras=%d",
        len(request.tokens),
        request.mode,
        len(request.loras) if request.loras else 0,
    )
    # Debug: Log LoRA details
    if request.loras:
        for lora in request.loras:
            logger.info("📥 [Prompt Compose] LoRA: name=%s, lora_type=%s", lora.name, lora.lora_type)

    # Prepare LoRA data
    lora_dicts = []
    lora_strings = []
    trigger_words = []
    lora_weights: dict[str, float] = {}

    if request.loras:
        for lora in request.loras:
            lora_dict = {
                "name": lora.name,
                "lora_type": lora.lora_type,
                "optimal_weight": lora.optimal_weight,
            }
            lora_dicts.append(lora_dict)

            if lora.trigger_words:
                trigger_words.extend(lora.trigger_words)

    # Detect complexity and calculate weights
    complexity = detect_scene_complexity(request.tokens)

    for lora in request.loras or []:
        weight = calculate_lora_weight(
            lora_type=lora.lora_type,
            complexity=complexity,
            optimal_weight=lora.optimal_weight,
        )
        lora_weights[lora.name] = weight
        lora_strings.append(f"<lora:{lora.name}:{weight}>")

    # Determine effective mode
    effective_mode = get_effective_mode_from_dict(request.mode, lora_dicts)

    # Compose prompt
    composed_tokens = compose_prompt_tokens(
        tokens=request.tokens,
        mode=effective_mode,
        lora_strings=lora_strings,
        trigger_words=trigger_words,
        use_break=request.use_break,
    )

    prompt_string = ", ".join(composed_tokens)

    logger.info(
        "✅ [Prompt Compose] mode=%s, complexity=%s, prompt=%d chars",
        effective_mode,
        complexity,
        len(prompt_string),
    )

    return PromptComposeResponse(
        prompt=prompt_string,
        tokens=composed_tokens,
        effective_mode=effective_mode,
        scene_complexity=complexity,
        lora_weights=lora_weights if lora_weights else None,
        meta={
            "token_count": len(composed_tokens),
            "has_break": "BREAK" in composed_tokens,
            "quality_tags_added": composed_tokens[:3] == ["masterpiece", "best quality", "high quality"],
        },
    )
