"""Prompt manipulation endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
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
    detect_scene_complexity,
    rewrite_prompt,
    split_prompt_example,
    split_prompt_tokens,
    validate_identity_tags,
    validate_loras,
)
from services.prompt.v3_service import V3PromptService

router = APIRouter(prefix="/prompt", tags=["prompt"])


def _collect_context_tags(context_tags: dict) -> list[str]:
    """Flatten context_tags dict into a tag list."""
    tags: list[str] = []
    for key in ("expression", "pose", "action", "environment", "mood"):
        val = context_tags.get(key)
        if isinstance(val, list):
            tags.extend(val)
    for key in ("gaze", "camera"):
        val = context_tags.get(key)
        if isinstance(val, str) and val:
            tags.append(val)
    return tags


def _convert_loras(loras: list | None) -> list[dict] | None:
    """Convert PromptComposeLoRA list to V3 style_loras dicts."""
    if not loras:
        return None
    return [
        {
            "name": l.name,
            "weight": l.weight,
            "trigger_words": l.trigger_words or [],
        }
        for l in loras
    ]


def check_tag_conflicts(tags: list[str], db) -> dict:
    """Stub: Check for tag conflicts."""
    return {
        "conflicts": [],
        "has_conflicts": False,
        "total_tags": len(tags)
    }


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
async def compose_prompt(
    request: PromptComposeRequest,
    db: Session = Depends(get_db),
):
    """Compose a prompt using V3 12-Layer engine.

    When character_id is provided, uses V3PromptService with full
    character tags, LoRA triggers, and gender enhancement from DB.
    Otherwise uses V3PromptBuilder.compose() for generic composition.

    Accepts optional base_prompt (quality tags) and context_tags
    (scene context like expression, gaze, pose) which are merged
    into the token list before V3 composition.
    """
    logger.info(
        "📥 [Prompt Compose] character_id=%s, %d tokens, loras=%s",
        request.character_id,
        len(request.tokens),
        [lora.name for lora in (request.loras or [])],
    )

    try:
        # 1. Merge context_tags + scene tokens (character data loaded from DB via character_id)
        all_tokens: list[str] = []
        if request.context_tags:
            all_tokens.extend(_collect_context_tags(request.context_tags))
        all_tokens.extend(request.tokens)

        # 2. V3 engine composition (character tags, LoRAs, gender loaded from DB)
        v3_service = V3PromptService(db)
        composed_prompt = v3_service.generate_prompt_for_scene(
            character_id=request.character_id,
            scene_tags=all_tokens,
            style_loras=_convert_loras(request.loras),
        )

        # 3. Build response
        composed_tokens = split_prompt_tokens(composed_prompt)
        scene_complexity = detect_scene_complexity(request.tokens)
        effective_mode = "v3" if request.character_id else "standard"

        lora_weights = None
        if request.loras:
            lora_weights = {lora.name: lora.weight for lora in request.loras}

        logger.info(
            "✅ [Prompt Compose] mode=%s, %d tokens → %d composed",
            effective_mode,
            len(all_tokens),
            len(composed_tokens),
        )

        return {
            "prompt": composed_prompt,
            "tokens": composed_tokens,
            "effective_mode": effective_mode,
            "scene_complexity": scene_complexity,
            "lora_weights": lora_weights,
            "meta": {
                "token_count": len(composed_tokens),
                "has_break": "BREAK" in composed_tokens,
                "quality_tags_added": any(
                    t in composed_tokens for t in ["best_quality", "masterpiece"]
                ),
            },
        }

    except Exception as e:
        logger.exception("❌ [Prompt Compose Error]")
        raise HTTPException(status_code=500, detail=str(e))


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
    2. Known problematic tags via TagAliasCache
    3. Tag post count in Danbooru (if enabled)

    Returns validation results with warnings for risky tags.
    """
    from models.tag import Tag
    from services.keywords.db_cache import TagAliasCache

    logger.info("📥 [Validate Tags] tags=%d, check_danbooru=%s", len(request.tags), request.check_danbooru)

    risky_tags: list[str] = []
    unknown_in_db: list[str] = []
    warnings: list[dict] = []

    for tag in request.tags:
        # Check if risky (has alias replacement)
        replacement = TagAliasCache.get_replacement(tag)
        if replacement is not ...:
            risky_tags.append(tag)
            suggestion = replacement if replacement else None
            reason = "removed (no alternative)" if not replacement else "risky tag"
            warnings.append({"tag": tag, "reason": reason, "suggestion": suggestion})
            continue

        # Check DB existence
        normalized = tag.strip().replace(" ", "_")
        exists = db.query(Tag).filter(Tag.name == normalized).first()
        if not exists:
            unknown_in_db.append(tag)

    logger.info(
        "✅ [Validate Tags] risky=%d, unknown=%d",
        len(risky_tags), len(unknown_in_db),
    )

    return {
        "risky_tags": risky_tags,
        "unknown_in_db": unknown_in_db,
        "warnings": warnings,
        "total": len(request.tags),
    }


@router.post("/auto-replace")
async def replace_tags(request: AutoReplaceRequest):
    """Automatically replace known risky tags with safe alternatives.

    Uses TagAliasCache to replace problematic tags like "medium shot"
    with Danbooru-verified alternatives like "cowboy_shot".
    """
    from services.keywords.db_cache import TagAliasCache

    logger.info("📥 [Auto Replace] tags=%d", len(request.tags))

    replaced: list[str] = []
    replacements: list[dict] = []
    removed: list[str] = []

    for tag in request.tags:
        replacement = TagAliasCache.get_replacement(tag)
        if replacement is ...:
            # Not a risky tag, keep as-is
            replaced.append(tag)
        elif replacement is None:
            # Should be removed (no alternative)
            removed.append(tag)
            replacements.append({"from": tag, "to": None, "action": "removed"})
        else:
            # Replace with alternative
            replaced.append(replacement)
            replacements.append({"from": tag, "to": replacement, "action": "replaced"})

    replaced_count = sum(1 for r in replacements if r["action"] == "replaced")

    return {
        "original": request.tags,
        "replaced": replaced,
        "replacements": replacements,
        "replaced_count": replaced_count,
        "removed_count": len(removed),
        "removed": removed,
    }


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
