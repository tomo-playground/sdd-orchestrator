"""Prompt manipulation endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

import logic
from config import logger, SD_LORAS_URL
from schemas import PromptRewriteRequest, PromptSplitRequest, PromptValidateRequest
from services.prompt import validate_loras, detect_prompt_conflicts, validate_identity_tags

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
