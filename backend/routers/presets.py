"""Preset templates API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import (
    SHORTS_DURATIONS,
    STORYBOARD_LANGUAGES,
)
from schemas import PresetDetailResponse, PresetListResponse, PresetTopicsResponse
from services.presets import get_all_presets, get_preset, get_sample_topics

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=PresetListResponse)
async def list_presets():
    """Get all available storyboard presets.

    Returns presets with sample topics, default settings, and option lists.
    """
    from config import (  # noqa: PLC0415
        DEFAULT_CONTROLNET_WEIGHT,
        DEFAULT_IP_ADAPTER_WEIGHT,
        DEFAULT_MULTI_GEN_ENABLED,
        DEFAULT_TTS_ENGINE,
        DEFAULT_USE_CONTROLNET,
        DEFAULT_USE_IP_ADAPTER,
        READING_SPEED,
        SD_HI_RES_DENOISING_STRENGTH,
        SD_HI_RES_SCALE,
        SD_HI_RES_SECOND_PASS_STEPS,
        SD_HI_RES_UPSCALER,
        SD_SAMPLERS,
    )
    from config_pipelines import FAST_TRACK_SKIP_STAGES  # noqa: PLC0415

    return {
        "presets": get_all_presets(),
        "languages": STORYBOARD_LANGUAGES,
        "durations": SHORTS_DURATIONS,
        "reading_speed": READING_SPEED,
        "optional_steps": [],
        "pipeline_metadata": [],
        "generation_defaults": {
            "use_controlnet": DEFAULT_USE_CONTROLNET,
            "controlnet_weight": DEFAULT_CONTROLNET_WEIGHT,
            "use_ip_adapter": DEFAULT_USE_IP_ADAPTER,
            "ip_adapter_weight": DEFAULT_IP_ADAPTER_WEIGHT,
            "multi_gen_enabled": DEFAULT_MULTI_GEN_ENABLED,
        },
        "hi_res_defaults": {
            "scale": SD_HI_RES_SCALE,
            "upscaler": SD_HI_RES_UPSCALER,
            "second_pass_steps": SD_HI_RES_SECOND_PASS_STEPS,
            "denoising_strength": SD_HI_RES_DENOISING_STRENGTH,
        },
        "samplers": SD_SAMPLERS,
        "tts_engine": DEFAULT_TTS_ENGINE,
        "fast_track_skip_stages": FAST_TRACK_SKIP_STAGES,
    }


@router.get("/{preset_id}", response_model=PresetDetailResponse)
async def get_preset_detail(preset_id: str):
    """Get details for a specific preset."""
    preset = get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    return {
        "id": preset.id,
        "name": preset.name,
        "name_ko": preset.name_ko,
        "description": preset.description,
        "structure": preset.structure,
        "template": preset.template,
        "sample_topics": preset.sample_topics,
        "default_duration": preset.default_duration,
        "default_style": preset.default_style,
        "default_language": preset.default_language,
        "extra_fields": preset.extra_fields,
    }


@router.get("/{preset_id}/topics", response_model=PresetTopicsResponse)
async def get_preset_topics(preset_id: str):
    """Get sample topics for a preset."""
    topics = get_sample_topics(preset_id)
    if not topics:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    return {"topics": topics}
