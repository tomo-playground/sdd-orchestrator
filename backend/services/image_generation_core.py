"""
Unified image generation core for Lab + Studio.
Provides single source of truth for V3 Prompt Engine + SD integration.
"""

from __future__ import annotations

import json
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import (
    SD_BASE_URL,
    SD_DEFAULT_CFG_SCALE,
    SD_DEFAULT_CLIP_SKIP,
    SD_DEFAULT_HEIGHT,
    SD_DEFAULT_SAMPLER,
    SD_DEFAULT_STEPS,
    SD_DEFAULT_WIDTH,
    SD_TIMEOUT_SECONDS,
    SD_TXT2IMG_URL,
    logger,
)
from services.prompt.prompt import normalize_negative_prompt, split_prompt_tokens
from services.prompt.v3_composition import V3PromptBuilder


async def _ensure_correct_checkpoint(sd_model_name: str) -> None:
    """Switch SD WebUI checkpoint if it doesn't match the StyleProfile's model.

    Non-blocking: logs warning on failure but does not raise.
    """
    if not sd_model_name:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{SD_BASE_URL}/sdapi/v1/options")
            if resp.status_code != 200:
                logger.warning("Failed to read SD options: %d", resp.status_code)
                return
            current_model = resp.json().get("sd_model_checkpoint", "")
            if sd_model_name in current_model:
                return  # Already using the correct checkpoint
            logger.info(
                "Switching SD checkpoint: %s -> %s",
                current_model,
                sd_model_name,
            )
            resp = await client.post(
                f"{SD_BASE_URL}/sdapi/v1/options",
                json={"sd_model_checkpoint": sd_model_name},
                timeout=120,
            )
            if resp.status_code == 200:
                logger.info("SD checkpoint switched to %s", sd_model_name)
            else:
                logger.warning("Failed to switch checkpoint: %d", resp.status_code)
    except Exception as e:
        logger.warning("Checkpoint switch failed (non-blocking): %s", e)


class ImageGenerationResult(BaseModel):
    """Unified response for Lab + Studio image generation."""

    image: str  # base64
    seed: int
    final_prompt: str
    final_negative_prompt: str

    # LoRA metadata
    loras_applied: list[dict] = Field(default_factory=list)
    # [{"name": "...", "weight": 0.7, "source": "character|style"}]

    # ControlNet metadata (Studio only)
    controlnet_pose: str | None = None
    ip_adapter_reference: str | None = None
    environment_reference_id: int | None = None

    # Warnings
    warnings: list[str] = Field(default_factory=list)


async def generate_image_with_v3(
    db: Session,
    prompt: str | list[str],
    character_id: int | None = None,
    storyboard_id: int | None = None,
    group_id: int | None = None,
    style_loras: list[dict] | None = None,
    sd_params: dict | None = None,
    controlnet_config: dict | None = None,
    mode: Literal["studio", "lab"] = "studio",
    scene_id: int | None = None,
) -> ImageGenerationResult:
    """
    Generate image using V3 Prompt Engine + SD.

    Args:
        db: Database session
        prompt: Tag list (list[str]) or composed prompt (str)
        character_id: Character ID for Character LoRA
        storyboard_id: Storyboard ID for Style Profile (Studio)
        group_id: Group ID for Style Profile (Lab)
        style_loras: Explicit Style LoRA override
        sd_params: SD parameters (steps, cfg_scale, etc)
        controlnet_config: ControlNet/IP-Adapter config (Studio only)
        mode: "studio" or "lab"

    Returns:
        ImageGenerationResult with image, metadata, and warnings
    """
    mode_prefix = "🎬 [Studio]" if mode == "studio" else "🧪 [Lab]"
    logger.info(
        f"{mode_prefix} Generating image: character_id={character_id}, "
        f"group_id={group_id}, storyboard_id={storyboard_id}"
    )

    # 1. Normalize prompt to string
    if isinstance(prompt, list):
        prompt_str = ", ".join(prompt)
    else:
        prompt_str = prompt

    # 2. Resolve Style LoRAs
    warnings: list[str] = []
    if not style_loras:
        if group_id:
            style_loras = resolve_style_loras_from_group(group_id, db)
            logger.debug(f"{mode_prefix} Resolved {len(style_loras)} Style LoRAs from Group {group_id}")
        elif storyboard_id:
            style_loras = resolve_style_loras_from_storyboard(storyboard_id, db)
            logger.debug(f"{mode_prefix} Resolved {len(style_loras)} Style LoRAs from Storyboard {storyboard_id}")
        else:
            style_loras = []
            logger.warning(f"{mode_prefix} No group_id or storyboard_id, skipping Style LoRAs")

    # 3. Ensure correct SD checkpoint for the StyleProfile
    style_ctx = None
    if storyboard_id or group_id:
        from services.style_context import resolve_style_context, resolve_style_context_from_group

        if group_id:
            style_ctx = resolve_style_context_from_group(group_id, db)
        elif storyboard_id:
            style_ctx = resolve_style_context(storyboard_id, db)
        if style_ctx and style_ctx.sd_model_name:
            await _ensure_correct_checkpoint(style_ctx.sd_model_name)

    # 4. StyleProfile + V3 Composition via shared SSOT
    negative_prompt = sd_params.get("negative_prompt", "") if sd_params else ""
    if storyboard_id or group_id:
        try:
            final_prompt, negative_prompt, compose_warnings = compose_scene_with_style(
                raw_prompt=prompt_str,
                negative_prompt=negative_prompt,
                character_id=character_id,
                storyboard_id=storyboard_id or group_id,
                style_loras=style_loras or [],
                db=db,
                scene_id=scene_id,
            )
            warnings.extend(compose_warnings)
            logger.debug(f"{mode_prefix} compose_scene_with_style complete")
        except Exception as e:
            logger.error(f"{mode_prefix} Composition failed: {e}")
            if mode == "studio":
                raise
            final_prompt = prompt_str
            warnings.append(f"Composition failed: {e}")
    else:
        final_prompt = prompt_str
        logger.debug(f"{mode_prefix} No storyboard/group, using prompt as-is")

    # 5. Build SD payload — base from sd_params > config.py defaults
    steps = sd_params.get("steps", SD_DEFAULT_STEPS) if sd_params else SD_DEFAULT_STEPS
    cfg_scale = sd_params.get("cfg_scale", SD_DEFAULT_CFG_SCALE) if sd_params else SD_DEFAULT_CFG_SCALE
    sampler_name = sd_params.get("sampler", SD_DEFAULT_SAMPLER) if sd_params else SD_DEFAULT_SAMPLER
    clip_skip = sd_params.get("clip_skip", SD_DEFAULT_CLIP_SKIP) if sd_params else SD_DEFAULT_CLIP_SKIP

    # StyleProfile DB 값 우선 적용 (preview.py 패턴과 동일)
    if style_ctx:
        if style_ctx.default_steps is not None:
            steps = style_ctx.default_steps
        if style_ctx.default_cfg_scale is not None:
            cfg_scale = style_ctx.default_cfg_scale
        if style_ctx.default_sampler_name:
            sampler_name = style_ctx.default_sampler_name
        if style_ctx.default_clip_skip is not None:
            clip_skip = style_ctx.default_clip_skip

    payload = {
        "prompt": final_prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler_name,
        "override_settings": {
            "CLIP_stop_at_last_layers": max(1, int(clip_skip)),
        },
        "override_settings_restore_afterwards": True,
        "width": sd_params.get("width", SD_DEFAULT_WIDTH) if sd_params else SD_DEFAULT_WIDTH,
        "height": sd_params.get("height", SD_DEFAULT_HEIGHT) if sd_params else SD_DEFAULT_HEIGHT,
        "seed": sd_params.get("seed", -1) if sd_params else -1,
    }

    # 6. Apply ControlNet/IP-Adapter (Studio only)
    if mode == "studio" and controlnet_config:
        # TODO: Integrate ControlNet/IP-Adapter logic
        pass

    # 7. Call SD API
    try:
        async with httpx.AsyncClient(timeout=SD_TIMEOUT_SECONDS) as client:
            resp = await client.post(SD_TXT2IMG_URL, json=payload)

        if resp.status_code != 200:
            msg = f"SD API error: {resp.status_code}"
            logger.error(f"{mode_prefix} {msg}")
            raise RuntimeError(msg)

        data = resp.json()
        info = json.loads(data.get("info", "{}"))
        resolved_seed = info.get("seed", payload["seed"])

        logger.info(f"{mode_prefix} Image generated successfully (seed={resolved_seed})")

        return ImageGenerationResult(
            image=data["images"][0],
            seed=resolved_seed,
            final_prompt=final_prompt,
            final_negative_prompt=negative_prompt,
            loras_applied=_extract_loras_from_prompt(final_prompt),
            warnings=warnings,
        )

    except Exception as e:
        logger.exception(f"{mode_prefix} SD API call failed")
        if mode == "studio":
            raise
        else:
            # Lab: return partial result
            return ImageGenerationResult(
                image="",
                seed=-1,
                final_prompt=final_prompt,
                final_negative_prompt=negative_prompt,
                warnings=[*warnings, f"SD API failed: {e}"],
            )


def compose_scene_with_style(
    *,
    raw_prompt: str,
    negative_prompt: str,
    character_id: int | None,
    storyboard_id: int | None,
    style_loras: list[dict],
    db: Session,
    scene_id: int | None = None,
    scene_character_actions: list[dict] | None = None,
    character_b_id: int | None = None,
    background_tags: list[str] | None = None,
    clothing_override: list[str] | None = None,
) -> tuple[str, str, list[str]]:
    """Compose scene prompt: StyleProfile + V3 composition (SSOT).

    Shared by Studio Direct (generation.py) and Creative Lab (creative_studio.py).
    Flow matches Studio Direct exactly:
      1. apply_style_profile_to_prompt(skip_loras=True) → quality tags + embeddings
      2. V3 compose_for_character / compose → character tags + LoRA injection
      3. Merge character custom_negative_prompt (if character_id)
      4. Detect non-Danbooru tags → warnings

    scene_character_actions can be provided directly (e.g. from context_tags)
    or resolved from DB via scene_id. Direct takes precedence over DB lookup.

    Returns: (composed_prompt, modified_negative_prompt, warnings)
    """
    from models.character import Character
    from services.generation import apply_style_profile_to_prompt
    from services.style_context import resolve_style_context

    warnings: list[str] = []

    # 1. Apply style profile embedding triggers (LoRAs + quality handled by V3 L0)
    styled_prompt, modified_negative = apply_style_profile_to_prompt(
        raw_prompt, negative_prompt, storyboard_id, db, skip_loras=True, skip_quality=True
    )

    # 2. V3 composition
    scene_tags = split_prompt_tokens(styled_prompt)

    # Merge background tags into scene tags (dedup to avoid duplicate environment tokens)
    if background_tags:
        from services.prompt.prompt import merge_tags_dedup

        scene_tags = merge_tags_dedup(scene_tags, background_tags)

    # Resolve StyleContext once: sd_model_base + quality_tags
    sd_model_base: str | None = None
    quality_tags: list[str] | None = None
    style_ctx = resolve_style_context(storyboard_id, db) if storyboard_id else None
    if style_ctx:
        sd_model_base = style_ctx.sd_model_base or None
        if style_ctx.default_positive:
            quality_tags = split_prompt_tokens(style_ctx.default_positive)

    builder = V3PromptBuilder(db, sd_model_base=sd_model_base)

    character = None
    if character_id:
        character = db.query(Character).filter(Character.id == character_id, Character.deleted_at.is_(None)).first()

    # Resolve scene-specific clothing override from DB
    if not clothing_override and scene_id and character_id:
        from models.scene import Scene as SceneModel

        scene_row = db.query(SceneModel).filter(SceneModel.id == scene_id, SceneModel.deleted_at.is_(None)).first()
        if scene_row and scene_row.clothing_tags:
            clothing_override = scene_row.clothing_tags.get(str(character_id))

    # Resolve scene-specific character actions from DB (skip if provided directly)
    if not scene_character_actions and scene_id:
        from models.associations import SceneCharacterAction

        sca_filter = SceneCharacterAction.scene_id == scene_id
        sca_rows = db.query(SceneCharacterAction).filter(sca_filter).all()
        if sca_rows:
            scene_character_actions = [
                {"character_id": a.character_id, "tag_id": a.tag_id, "weight": a.weight} for a in sca_rows
            ]

    # Multi-character routing
    char_b = None
    if character and character_b_id:
        from services.prompt.v3_multi_character import MultiCharacterComposer

        char_b = db.query(Character).filter(Character.id == character_b_id, Character.deleted_at.is_(None)).first()
        if char_b:
            composer = MultiCharacterComposer(builder)
            composed = composer.compose(
                character,
                char_b,
                scene_tags,
                style_loras=style_loras,
                scene_character_actions=scene_character_actions,
                quality_tags=quality_tags,
            )
        else:
            composed = builder.compose_for_character(
                character.id,
                scene_tags,
                style_loras=style_loras,
                character=character,
                scene_character_actions=scene_character_actions,
                clothing_override=clothing_override,
                quality_tags=quality_tags,
            )
    elif character:
        composed = builder.compose_for_character(
            character.id,
            scene_tags,
            style_loras=style_loras,
            character=character,
            scene_character_actions=scene_character_actions,
            clothing_override=clothing_override,
            quality_tags=quality_tags,
        )
    else:
        composed = builder.compose(scene_tags, style_loras=style_loras, quality_tags=quality_tags)

    # 3. Merge character negative prompts (custom + recommended, both chars)
    for char in [character, char_b]:
        if not char:
            continue
        if char.custom_negative_prompt:
            modified_negative = f"{modified_negative}, {char.custom_negative_prompt}"
        if char.recommended_negative:
            modified_negative = f"{modified_negative}, {', '.join(char.recommended_negative)}"

    # 4. Merge builder warnings (LoRA compatibility, etc.)
    warnings.extend(builder.warnings)

    # 5. Detect non-Danbooru tags
    unknown = builder.find_unknown_tags(scene_tags)
    if unknown:
        warnings.append(f"Non-Danbooru tags detected: {', '.join(unknown)}")
        logger.warning("[compose] Non-Danbooru tags: %s", unknown)

    logger.debug(
        "🎨 [compose_scene_with_style] char_id=%s, storyboard_id=%s, loras=%d",
        character_id,
        storyboard_id,
        len(style_loras),
    )

    return composed, normalize_negative_prompt(modified_negative), warnings


def resolve_style_loras_from_group(group_id: int, db: Session) -> list[dict]:
    """Resolve Style LoRAs from Group Config via resolve_effective_config cascade.

    Delegates to style_context module (SSOT) for DB cascade + LoRA resolution.
    """
    from services.style_context import extract_style_loras, resolve_style_context_from_group

    ctx = resolve_style_context_from_group(group_id, db)
    result = extract_style_loras(ctx)
    logger.debug("Resolved %d Style LoRAs from Group %d", len(result), group_id)
    return result


def resolve_style_loras_from_storyboard(storyboard_id: int, db: Session) -> list[dict]:
    """Resolve Style LoRAs from Storyboard (via Group Config)."""
    from models import Storyboard

    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard or not storyboard.group_id:
        logger.warning(f"Storyboard {storyboard_id} has no group_id")
        return []

    return resolve_style_loras_from_group(storyboard.group_id, db)


def _extract_loras_from_prompt(prompt: str) -> list[dict]:
    """
    Extract LoRA metadata from final prompt.

    Args:
        prompt: Final prompt string containing LoRA tags (e.g., "1girl, <lora:char:1.0>, <lora:anime:0.7>")

    Returns:
        List of LoRA metadata dicts with keys:
        - name (str): LoRA name
        - weight (float): LoRA weight
        - source (str): LoRA type from DB ("character", "style", "pose", etc.)
          Falls back to "unknown" if not found in cache.

    Regex Pattern:
        <lora:NAME:WEIGHT> where NAME is alphanumeric/underscore, WEIGHT is float
    """
    from services.keywords.db_cache import LoRATriggerCache

    loras = []
    pattern = r"<lora:([^:]+):([0-9.]+)>"
    for match in re.finditer(pattern, prompt):
        name = match.group(1)
        weight = float(match.group(2))
        # Resolve source from DB via LoRATriggerCache (name -> lora_type)
        lora_type = LoRATriggerCache.get_lora_type(name)
        loras.append(
            {
                "name": name,
                "weight": weight,
                "source": lora_type or "unknown",
            }
        )
    return loras
