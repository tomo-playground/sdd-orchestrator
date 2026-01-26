"""Prompt manipulation endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import SD_LORAS_URL, logger
from database import get_db
from schemas import (
    PromptComposeRequest,
    PromptComposeResponse,
    PromptRewriteRequest,
    PromptSplitRequest,
    PromptValidateRequest,
)
from services.prompt import (
    detect_prompt_conflicts,
    rewrite_prompt,
    split_prompt_example,
    validate_identity_tags,
    validate_loras,
)
from services.prompt_composition import (
    calculate_lora_weight,
    compose_prompt_tokens,
    detect_scene_complexity,
    get_effective_mode_from_dict,
)
from services.prompt_validation import auto_replace_risky_tags, check_tag_conflicts, validate_prompt_tags

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/rewrite")
async def rewrite_prompt_endpoint(request: PromptRewriteRequest):
    logger.info("📥 [Prompt Rewrite Req] %s", request.model_dump())
    return rewrite_prompt(request)


@router.post("/split")
async def split_prompt_endpoint(request: PromptSplitRequest):
    logger.info("📥 [Prompt Split Req] %s", request.model_dump())
    return split_prompt_example(request)


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
    - composed_prompt: Final merged prompt string
    - effective_mode: "standard" or "lora"
    - token_count: Number of tokens in composed prompt
    - lora_weight: Adjusted LoRA weight (Mode B only)
    - scene_complexity: Scene complexity score (Mode B only)
    """
    logger.info(
        "📥 [Prompt Compose] mode=%s, %d tokens, loras=%s",
        request.mode,
        len(request.tokens),
        [lora.name for lora in (request.loras or [])],
    )

    # Detect effective mode
    effective_mode = get_effective_mode_from_dict(request.model_dump())

    # Extract LoRA strings and trigger words (if Mode B)
    lora_strings = []
    trigger_words = []
    if effective_mode == "lora" and request.loras:
        for lora in request.loras:
            lora_strings.append(f"<lora:{lora.name}:{lora.weight}>")
            if lora.trigger_words:
                trigger_words.extend(lora.trigger_words)

    # Compose prompt tokens
    composed_tokens = compose_prompt_tokens(
        tokens=request.tokens,
        mode=effective_mode,
        lora_strings=lora_strings,
        trigger_words=trigger_words,
        use_break=request.use_break if request.use_break is not None else True,
    )

    # Build final prompt string
    composed_prompt = ", ".join(composed_tokens)

    # Calculate metadata
    result_metadata = {
        "composed_prompt": composed_prompt,
        "effective_mode": effective_mode,
        "token_count": len(composed_tokens),
    }

    # Mode B specific metadata
    if effective_mode == "lora" and request.loras:
        scene_complexity = detect_scene_complexity(request.tokens)
        adjusted_weight = calculate_lora_weight(
            base_weight=request.loras[0].weight,
            scene_complexity=scene_complexity,
        )
        result_metadata["lora_weight"] = adjusted_weight
        result_metadata["scene_complexity"] = scene_complexity

    logger.info(
        "✅ [Prompt Compose] mode=%s, %d tokens → %d composed",
        effective_mode,
        len(request.tokens),
        len(composed_tokens),
    )

    return result_metadata


class ValidateTagsRequest(BaseModel):
    """Request body for tag validation."""

    tags: list[str]
    check_danbooru: bool = True


class AutoReplaceRequest(BaseModel):
    """Request body for auto-replacement."""

    tags: list[str]


@router.post("/validate-tags")
async def validate_tags(
    request: ValidateTagsRequest,
    db: Session = Depends(get_db),
):
    """Validate prompt tags against DB and Danbooru.

    Checks:
    1. Tag existence in local DB
    2. Tag post count in Danbooru (if enabled)
    3. Known problematic tags (e.g., "medium shot")

    Returns validation results with warnings for risky tags.
    """
    logger.info("📥 [Validate Tags] tags=%d, check_danbooru=%s", len(request.tags), request.check_danbooru)

    result = validate_prompt_tags(
        tags=request.tags,
        check_danbooru=request.check_danbooru,
        db=db,
    )

    logger.info(
        "✅ [Validate Tags] risky=%d, unknown=%d, low_posts=%d",
        len(result["risky"]),
        len(result["unknown"]),
        len(result.get("low_post_count", [])),
    )

    return {
        "risky_tags": result["risky"],
        "unknown_in_db": result["unknown"],
        "low_post_count": result.get("low_post_count", []),
        "warnings": result["warnings"],
        "total": result["total_tags"],
    }


@router.post("/auto-replace")
async def replace_tags(request: AutoReplaceRequest):
    """Automatically replace known risky tags with safe alternatives.

    Replaces problematic tags like "medium shot" with Danbooru-verified alternatives
    like "cowboy shot".

    Returns replacement results with original/replaced tags.
    """
    logger.info("📥 [Auto Replace] tags=%d", len(request.tags))

    result = auto_replace_risky_tags(tags=request.tags)

    logger.info("✅ [Auto Replace] replaced=%d tags", result["replaced_count"])

    return result


class CheckConflictsRequest(BaseModel):
    """Request for checking tag conflicts."""

    tags: list[str]


@router.post("/check-conflicts")
async def check_conflicts(
    request: CheckConflictsRequest,
    db: Session = Depends(get_db),
):
    """Check for tag conflicts using DB rules.

    Returns:
        {
            "has_conflicts": bool,
            "conflicts": [
                {
                    "tag1": str,
                    "tag2": str,
                    "reason": str (optional)
                }
            ],
            "filtered_tags": list[str]  # Tags with conflicts removed
        }
    """
    result = check_tag_conflicts(request.tags, db)
    logger.info(
        "✅ [Check Conflicts] %d conflicts found in %d tags",
        len(result["conflicts"]),
        len(request.tags),
    )
    return result
