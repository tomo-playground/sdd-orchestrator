"""Style Profile application for generation pipeline.

Extracted from generation.py for module size compliance.
"""

from __future__ import annotations

import re

from config import cap_style_lora_weight, logger
from services.keywords.core import normalize_prompt_token
from services.prompt import split_prompt_tokens
from services.prompt.v3_composition import select_style_trigger_words


def apply_style_profile_to_prompt(
    prompt: str,
    negative_prompt: str,
    storyboard_id: int | None,
    db,
    *,
    skip_loras: bool = False,
    skip_quality: bool = False,
) -> tuple[str, str]:
    """Apply Style Profile settings from Storyboard to prompt.

    Args:
        skip_quality: True이면 quality tags(default_positive) prepend를 건너뛴다.
            V3 Builder가 L0에 직접 배치할 때 이중 주입 방지.

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

        lora_tags, trigger_words = _build_lora_parts(ctx, prompt, skip_loras)
        modified_prompt = _compose_positive(ctx, prompt, lora_tags, trigger_words, skip_quality=skip_quality)
        modified_negative = _compose_negative(ctx, negative_prompt)

        logger.info(
            "✅ [Style Profile] Applied %d LoRAs, %d trigger words, %d pos embeds, %d neg embeds",
            len(lora_tags),
            len(trigger_words),
            len(ctx.positive_embeddings),
            len(ctx.negative_embeddings),
        )
        logger.info("📝 [Style Profile] Final prompt: %s", modified_prompt[:200])

        return modified_prompt, modified_negative

    except Exception as e:
        logger.error(f"❌ [Style Profile] Error applying profile: {e}")
        return prompt, negative_prompt


def _build_lora_parts(ctx, prompt: str, skip_loras: bool) -> tuple[list[str], list[str]]:
    """Build LoRA tags and trigger words, deduplicating against existing prompt."""
    lora_tags: list[str] = []
    trigger_words: list[str] = []

    if ctx.loras and not skip_loras:
        for lr in ctx.loras:
            if lr.get("trigger_words"):
                tw = select_style_trigger_words(lr["trigger_words"], lr.get("lora_type"))
                trigger_words.extend(tw)
            weight = cap_style_lora_weight(lr["weight"], lr.get("lora_type"))
            lora_tags.append(f"<lora:{lr['name']}:{weight}>")

    # Defense-in-depth: skip LoRA tags/trigger words already in prompt
    existing_lora_names = set(re.findall(r"<lora:([^:]+):", prompt))
    if existing_lora_names:
        existing_normalized = {
            normalize_prompt_token(t) for t in split_prompt_tokens(prompt) if normalize_prompt_token(t)
        }
        lora_tags = [t for t in lora_tags if re.search(r"<lora:([^:]+):", t).group(1) not in existing_lora_names]
        trigger_words = [tw for tw in trigger_words if normalize_prompt_token(tw) not in existing_normalized]

    return lora_tags, trigger_words


def _compose_positive(
    ctx, prompt: str, lora_tags: list[str], trigger_words: list[str], *, skip_quality: bool = False
) -> str:
    """Compose final positive prompt with deduplication."""
    existing_normalized = {normalize_prompt_token(t) for t in split_prompt_tokens(prompt) if normalize_prompt_token(t)}
    parts: list[str] = []

    # 1. Default positive prompt (quality tags), skip tokens already in prompt
    # skip_quality=True: V3 Builder가 L0에 직접 배치 → 여기선 건너뜀
    if ctx.default_positive and not skip_quality:
        new_tokens = [
            t for t in split_prompt_tokens(ctx.default_positive) if normalize_prompt_token(t) not in existing_normalized
        ]
        if new_tokens:
            parts.append(", ".join(new_tokens))

    # 2. Trigger words (deduplicated in _build_lora_parts)
    if trigger_words:
        parts.append(", ".join(trigger_words))

    # 3. Positive embedding triggers
    if ctx.positive_embeddings:
        parts.append(", ".join(ctx.positive_embeddings))

    # 4. Original prompt
    if prompt:
        parts.append(prompt.strip())

    # 5. LoRA tags (at the end)
    if lora_tags:
        parts.append(", ".join(lora_tags))

    return ", ".join(parts)


def _compose_negative(ctx, negative_prompt: str) -> str:
    """Compose final negative prompt: default_negative > embeddings > user input."""
    parts: list[str] = []
    if ctx.default_negative:
        parts.append(ctx.default_negative)
    if ctx.negative_embeddings:
        parts.append(", ".join(ctx.negative_embeddings))
    if negative_prompt:
        parts.append(negative_prompt)
    return ", ".join(parts)
