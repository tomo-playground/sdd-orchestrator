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
    SD_DEFAULT_CFG_SCALE,
    SD_DEFAULT_HEIGHT,
    SD_DEFAULT_SAMPLER,
    SD_DEFAULT_STEPS,
    SD_DEFAULT_WIDTH,
    SD_TIMEOUT_SECONDS,
    SD_TXT2IMG_URL,
    logger,
)
from services.prompt.v3_composition import V3PromptBuilder


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

    # 1. Normalize prompt
    if isinstance(prompt, list):
        scene_tags = prompt
        prompt_str = ", ".join(prompt)
        logger.debug(f"{mode_prefix} Prompt type: list[str] → joined")
    else:
        prompt_str = prompt
        scene_tags = _split_prompt_tokens(prompt)
        logger.debug(f"{mode_prefix} Prompt type: str")

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

    # 3. V3 Composition (Character LoRA + Scene Tags + Style LoRAs)
    if character_id:
        try:
            builder = V3PromptBuilder(db)
            final_prompt = builder.compose_for_character(
                character_id=character_id,
                scene_tags=scene_tags,
                style_loras=style_loras,
            )
            logger.debug(f"{mode_prefix} V3 composition complete")
        except Exception as e:
            logger.error(f"{mode_prefix} V3 composition failed: {e}")
            if mode == "studio":
                raise
            else:
                # Lab: fallback to prompt without V3
                final_prompt = prompt_str
                warnings.append(f"V3 composition failed: {e}")
    else:
        final_prompt = prompt_str
        logger.debug(f"{mode_prefix} No character_id, using prompt as-is")

    # 4. Apply Style Profile (Quality Tags + Negative)
    negative_prompt = sd_params.get("negative_prompt", "") if sd_params else ""
    if storyboard_id or group_id:
        from services.generation import apply_style_profile_to_prompt

        try:
            final_prompt, negative_prompt = apply_style_profile_to_prompt(
                final_prompt,
                negative_prompt,
                storyboard_id or group_id,
                db,
                skip_loras=True,  # V3 already applied LoRAs
            )
            logger.debug(f"{mode_prefix} Style Profile applied")
        except Exception as e:
            logger.warning(f"{mode_prefix} Style Profile failed: {e}")
            warnings.append(f"Style Profile failed: {e}")

    # 5. Build SD payload
    payload = {
        "prompt": final_prompt,
        "negative_prompt": negative_prompt,
        "steps": sd_params.get("steps", SD_DEFAULT_STEPS) if sd_params else SD_DEFAULT_STEPS,
        "cfg_scale": sd_params.get("cfg_scale", SD_DEFAULT_CFG_SCALE) if sd_params else SD_DEFAULT_CFG_SCALE,
        "sampler_name": (sd_params.get("sampler", SD_DEFAULT_SAMPLER) if sd_params else SD_DEFAULT_SAMPLER),
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


def resolve_style_loras_from_group(group_id: int, db: Session) -> list[dict]:
    """Resolve Style LoRAs from Group Config."""
    from models import LoRA, StyleProfile
    from models.group import Group
    from models.group_config import GroupConfig

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group or not group.config:
        logger.warning(f"Group {group_id} has no config")
        return []

    config: GroupConfig = group.config
    if not config.style_profile_id:
        logger.warning(f"Group {group_id} has no style_profile_id")
        return []

    profile = db.query(StyleProfile).filter(StyleProfile.id == config.style_profile_id).first()
    if not profile or not profile.loras:
        return []

    result = []
    for lora_config in profile.loras:
        lora_id = lora_config.get("lora_id")
        weight = lora_config.get("weight", 0.7)
        if not lora_id:
            continue
        lora_obj = db.query(LoRA).filter(LoRA.id == lora_id).first()
        if not lora_obj:
            continue
        result.append(
            {
                "name": lora_obj.name,
                "weight": weight,
                "trigger_words": (list(lora_obj.trigger_words) if lora_obj.trigger_words else []),
            }
        )

    logger.debug(f"Resolved {len(result)} Style LoRAs from Group {group_id}")
    return result


def resolve_style_loras_from_storyboard(storyboard_id: int, db: Session) -> list[dict]:
    """Resolve Style LoRAs from Storyboard (via Group Config)."""
    from models import Storyboard

    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard or not storyboard.group_id:
        logger.warning(f"Storyboard {storyboard_id} has no group_id")
        return []

    return resolve_style_loras_from_group(storyboard.group_id, db)


def _split_prompt_tokens(prompt: str) -> list[str]:
    """
    Split prompt string into individual tag tokens.

    Args:
        prompt: Comma-separated tag string (e.g., "1girl, smile, blue_eyes")

    Returns:
        List of individual tag strings with whitespace stripped
    """
    return [t.strip() for t in prompt.split(",") if t.strip()]


def _extract_loras_from_prompt(prompt: str) -> list[dict]:
    """
    Extract LoRA metadata from final prompt.

    Args:
        prompt: Final prompt string containing LoRA tags (e.g., "1girl, <lora:char:1.0>, <lora:anime:0.7>")

    Returns:
        List of LoRA metadata dicts with keys:
        - name (str): LoRA name
        - weight (float): LoRA weight
        - source (str): "character" or "style" (inferred from name)

    Regex Pattern:
        <lora:NAME:WEIGHT> where NAME is alphanumeric/underscore, WEIGHT is float
    """
    loras = []
    pattern = r"<lora:([^:]+):([0-9.]+)>"
    for match in re.finditer(pattern, prompt):
        name = match.group(1)
        weight = float(match.group(2))
        loras.append(
            {
                "name": name,
                "weight": weight,
                "source": "character" if "character" in name.lower() else "style",
            }
        )
    return loras
