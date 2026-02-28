from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from config import (
    DEFAULT_CONTROLNET_WEIGHT,
    DEFAULT_IP_ADAPTER_WEIGHT,
    DEFAULT_MULTI_GEN_ENABLED,
    DEFAULT_SPEAKER,
    DEFAULT_STRUCTURE,
    DEFAULT_USE_CONTROLNET,
    DEFAULT_USE_IP_ADAPTER,
    SD_DEFAULT_CFG_SCALE,
    SD_DEFAULT_HEIGHT,
    SD_DEFAULT_SAMPLER,
    SD_DEFAULT_STEPS,
    SD_DEFAULT_WIDTH,
)

logger = logging.getLogger(__name__)


class CharacterLoRA(BaseModel):
    lora_id: int
    weight: float = 1.0
    name: str | None = None
    trigger_words: list[str] | None = None
    lora_type: str | None = None


# ============================================================
# Project / Group Schemas
# ============================================================


class ProjectCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    handle: str | None = Field(default=None, max_length=100)
    avatar_media_asset_id: int | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    handle: str | None = Field(default=None, max_length=100)
    avatar_media_asset_id: int | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    handle: str | None = None
    avatar_media_asset_id: int | None = None
    avatar_url: str | None = None  # Read-only from @property
    avatar_key: str | None = None  # Read-only from @property (storage key for rendering)
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RenderPresetCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    bgm_file: str | None = None
    bgm_volume: float | None = None
    audio_ducking: bool | None = None
    scene_text_font: str | None = None
    layout_style: str | None = None
    frame_style: str | None = None
    transition_type: str | None = None
    ken_burns_preset: str | None = None
    ken_burns_intensity: float | None = None
    speed_multiplier: float | None = None
    bgm_mode: Literal["manual", "auto"] = "manual"
    music_preset_id: int | None = None


class RenderPresetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    bgm_file: str | None = None
    bgm_volume: float | None = None
    audio_ducking: bool | None = None
    scene_text_font: str | None = None
    layout_style: str | None = None
    frame_style: str | None = None
    transition_type: str | None = None
    ken_burns_preset: str | None = None
    ken_burns_intensity: float | None = None
    speed_multiplier: float | None = None
    bgm_mode: Literal["manual", "auto"] | None = None
    music_preset_id: int | None = None


class RenderPresetResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_system: bool = True
    bgm_file: str | None = None
    bgm_volume: float | None = None
    audio_ducking: bool | None = None
    scene_text_font: str | None = None
    layout_style: str | None = None
    frame_style: str | None = None
    transition_type: str | None = None
    ken_burns_preset: str | None = None
    ken_burns_intensity: float | None = None
    speed_multiplier: float | None = None
    bgm_mode: str = "manual"
    music_preset_id: int | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    project_id: int
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    render_preset_id: int | None = None
    style_profile_id: int | None = None
    narrator_voice_preset_id: int | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    render_preset_id: int | None = None
    style_profile_id: int | None = None
    narrator_voice_preset_id: int | None = None


class GroupResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None = None
    render_preset_id: int | None = None
    style_profile_id: int | None = None
    narrator_voice_preset_id: int | None = None
    # Response-only: derived from @property
    render_preset_name: str | None = None
    style_profile_name: str | None = None
    voice_preset_name: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EffectiveConfigResponse(BaseModel):
    """Resolved cascading config: System Default < Group (2-level)."""

    render_preset_id: int | None = None
    render_preset: RenderPresetResponse | None = None  # Full preset for frontend
    style_profile_id: int | None = None
    narrator_voice_preset_id: int | None = None
    sources: dict[str, str] = {}  # field -> "group" | "system_default"


# ============================================================
# Storyboard Schemas
# ============================================================


class StoryboardBase(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    group_id: int | None = None
    caption: str | None = Field(default=None, max_length=500)
    structure: str = DEFAULT_STRUCTURE
    duration: int | None = None
    language: str | None = None


class CastingRecommendationSchema(BaseModel):
    """Phase 20-C: AI casting recommendation persisted with storyboard."""

    character_id: int | None = None
    character_name: str = ""
    character_b_id: int | None = None
    character_b_name: str = ""
    structure: str | None = None
    style_profile_id: int | None = None
    reasoning: str = Field(default="", max_length=2000)


class StoryboardSave(StoryboardBase):
    character_id: int | None = None
    character_b_id: int | None = None
    version: int | None = None  # Optimistic locking: current version from client
    bgm_prompt: str | None = None  # Sound Designer recommendation.prompt
    bgm_mood: str | None = None  # Sound Designer recommendation.mood
    casting_recommendation: CastingRecommendationSchema | None = None
    scenes: list[StoryboardScene]


class StoryboardSaveResponse(BaseModel):
    """Response for POST/PUT /storyboards."""

    status: str
    storyboard_id: int
    scene_ids: list[int]
    client_ids: list[str]
    version: int = 1  # Current version after save


class StoryboardUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    caption: str | None = Field(default=None, max_length=2000)
    version: int | None = None  # Optimistic locking: current version from client


class StoryboardMetadataUpdateResponse(BaseModel):
    """Response for PATCH /storyboards/{id}/metadata."""

    status: str
    storyboard_id: int
    version: int


class StoryboardCastMember(BaseModel):
    id: int
    name: str
    speaker: str
    preview_url: str | None = None


class StoryboardListItem(BaseModel):
    id: int
    title: str
    description: str | None = None
    scene_count: int = 0
    image_count: int = 0
    cast: list[StoryboardCastMember] = []
    kanban_status: str = "draft"  # draft | in_prod | rendered | published
    stage_status: str | None = None  # pending | staging | staged | failed
    created_at: str | None = None
    updated_at: str | None = None


class StoryboardResponse(StoryboardBase):
    id: int
    video_url: str | None = None
    recent_videos: list[dict] | None = None
    deleted_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class RecentVideoResponse(BaseModel):
    """A recent render video entry."""

    url: str
    label: str | None = None
    createdAt: int  # Millisecond timestamp
    renderHistoryId: int | None = None


class SceneTagResponse(BaseModel):
    """Tag attached to a scene (read-only)."""

    tag_id: int
    weight: float = 1.0


class SceneActionResponse(BaseModel):
    """Character action attached to a scene (read-only)."""

    character_id: int
    tag_id: int
    tag_name: str | None = None  # Enriched from tag relationship
    weight: float = 1.0


class SceneDetailResponse(BaseModel):
    """Full scene detail returned from GET /storyboards/{id}."""

    id: int
    client_id: str
    scene_id: int
    script: str | None = ""
    speaker: str | None = ""
    duration: float | None = 3.0
    scene_mode: Literal["single", "multi"] = "single"
    image_prompt: str | None = ""
    image_prompt_ko: str | None = ""
    negative_prompt: str | None = None
    # Response-only: derived from Scene.image_asset @property
    image_url: str | None = None
    width: int = 512
    height: int = 768
    context_tags: dict | None = None
    clothing_tags: dict | None = None  # Per-scene clothing override
    tags: list[SceneTagResponse] = []
    character_actions: list[SceneActionResponse] = []
    use_reference_only: bool | None = None
    reference_only_weight: float | None = None
    background_id: int | None = None
    environment_reference_id: int | None = None
    environment_reference_weight: float | None = None
    image_asset_id: int | None = None
    candidates: list[SceneCandidate] | None = None
    auto_pin_previous: bool = Field(default=False, alias="_auto_pin_previous")

    # Per-scene generation settings override (null = inherit global)
    use_controlnet: bool | None = None
    controlnet_weight: float | None = None
    controlnet_pose: str | None = None
    use_ip_adapter: bool | None = None
    ip_adapter_reference: str | None = None
    ip_adapter_weight: float | None = None
    multi_gen_enabled: bool | None = None
    voice_design_prompt: str | None = None
    head_padding: float | None = None
    tail_padding: float | None = None

    model_config = ConfigDict(populate_by_name=True)


class StoryboardCharacterResponse(BaseModel):
    """Character cast info for a storyboard."""

    speaker: str  # "A", "B"
    character_id: int
    character_name: str
    preview_image_url: str | None = None  # Response-only: derived from Character.preview_image_url


class StoryboardDetailResponse(BaseModel):
    """Full storyboard detail returned from GET /storyboards/{id}."""

    id: int
    title: str
    description: str | None = None
    group_id: int | None = None
    project_id: int | None = None
    structure: str = DEFAULT_STRUCTURE
    duration: int | None = None
    language: str | None = None
    version: int = 1  # Optimistic locking version
    character_id: int | None = None
    character_b_id: int | None = None
    style_profile_id: int | None = None
    narrator_voice_preset_id: int | None = None
    video_url: str | None = None
    recent_videos: list[RecentVideoResponse] = []
    caption: str | None = None
    bgm_prompt: str | None = None  # Sound Designer recommendation
    bgm_mood: str | None = None  # Sound Designer mood tag
    stage_status: str | None = None  # pending | staging | staged | failed
    casting_recommendation: CastingRecommendationSchema | None = None
    created_at: str | None = None
    updated_at: str | None = None
    characters: list[StoryboardCharacterResponse] = []
    scenes: list[SceneDetailResponse] = []


class StoryboardRequest(BaseModel):
    topic: str = Field(max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    duration: int = 10
    style: str = "Anime"
    language: str = "Korean"
    structure: str = DEFAULT_STRUCTURE
    actor_a_gender: str = "female"
    character_id: int | None = None
    character_b_id: int | None = None
    group_id: int | None = None
    preset: str | None = None  # "express" | "standard" | "creator"
    skip_stages: list[str] | None = None  # ["research", "concept", "production", "explain"]
    references: list[str] | None = Field(default=None, max_length=5)  # URL 또는 텍스트 (최대 5개)
    selected_concept: dict | None = None  # Critic 선정 컨셉 (title, concept, strengths)


class SceneCandidate(BaseModel):
    """Candidate image for scene selection."""

    media_asset_id: int
    match_rate: float | None = None
    adjusted_match_rate: float | None = None
    identity_score: float | None = None
    # Response-only: enriched on GET, excluded from JSONB storage
    image_url: str | None = None


class StoryboardScene(BaseModel):
    scene_id: int
    client_id: str | None = None
    script: str = Field(max_length=1000)
    speaker: str = DEFAULT_SPEAKER
    duration: float = 3
    scene_mode: Literal["single", "multi"] = "single"
    image_prompt: str = Field(default="", max_length=2000)
    image_prompt_ko: str = ""
    # Input-only: triggers _link_media_asset, not stored directly
    image_url: str | None = None
    width: int = 512
    height: int = 768

    # SD Generation Params
    negative_prompt: str | None = Field(default=None, max_length=2000)
    context_tags: dict | None = None
    clothing_tags: dict | None = None  # Per-scene clothing override

    # Candidate images (media_asset_id based)
    candidates: list[SceneCandidate] | None = None

    # V3 Data Persistence
    tags: list[SceneTagSave] | None = None
    character_actions: list[SceneActionSave] | None = None

    # Background asset reference
    background_id: int | None = None

    # Consistency Enhancements
    use_reference_only: bool | None = None
    reference_only_weight: float | None = None
    environment_reference_id: int | None = None
    environment_reference_weight: float | None = None
    image_asset_id: int | None = None

    # Per-scene generation settings override (null = inherit global)
    use_controlnet: bool | None = None
    controlnet_weight: float | None = None
    controlnet_pose: str | None = None
    use_ip_adapter: bool | None = None
    ip_adapter_reference: str | None = None
    ip_adapter_weight: float | None = None
    multi_gen_enabled: bool | None = None
    voice_design_prompt: str | None = None
    head_padding: float | None = None
    tail_padding: float | None = None

    model_config = ConfigDict(extra="allow")


class SceneTagSave(BaseModel):
    tag_id: int
    weight: float = 1.0


class SceneActionSave(BaseModel):
    character_id: int
    tag_id: int = 0
    tag_name: str | None = None  # Frontend may send tag_name when tag_id unknown
    weight: float = 1.0

    model_config = ConfigDict(extra="allow")


class TTSEngine(str, Enum):
    QWEN = "qwen"


class VideoScene(BaseModel):
    # Transient: FFmpeg rendering input, never stored
    image_url: str
    script: str = ""
    speaker: str = DEFAULT_SPEAKER
    duration: float = 3
    # Per-scene Ken Burns override (from Cinematographer agent)
    ken_burns_preset: str | None = None
    # Per-scene voice override
    narrator_voice: str | None = None
    voice_design_prompt: str | None = None
    head_padding: float = 0.0
    tail_padding: float = 0.0
    # Stage background ID (for transition auto-select & Ken Burns alternation)
    background_id: int | None = None
    # Emotion context for TTS voice design (from context_tags.emotion)
    scene_emotion: str | None = None
    # Korean scene description (for context-aware voice generation)
    image_prompt_ko: str | None = None

    model_config = ConfigDict(extra="allow")


class OverlaySettings(BaseModel):
    channel_name: str = "daily_shorts"
    avatar_key: str = "daily_shorts"
    likes_count: str = "12.5k"
    posted_time: str = "2분 전"
    caption: str = "Amazing video! #shorts"
    frame_style: str = "overlay_minimal.png"
    avatar_file: str | None = None


class PostCardSettings(BaseModel):
    channel_name: str = "creator"
    avatar_key: str = "creator"
    caption: str = ""


class VideoRequest(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _migrate_edge_to_qwen(cls, values):
        if isinstance(values, dict) and values.get("tts_engine") == "edge":
            logger.warning("[TTS] tts_engine='edge' deprecated, auto-converting to 'qwen'")
            values["tts_engine"] = "qwen"
        return values

    scenes: list[VideoScene]
    project_id: int | None = None
    group_id: int | None = None
    storyboard_id: int | None = None
    storyboard_title: str = Field(default="my_shorts", max_length=200)
    bgm_file: str | None = None
    width: int = 1080
    height: int = 1920
    layout_style: str = "post"
    ken_burns_preset: str = "random"  # Ken Burns preset (14 options, random for variety)
    ken_burns_intensity: float = 1.0  # Effect intensity (0.5~2.0)
    transition_type: str = "random"  # Scene transition effect (random for variety)
    narrator_voice: str = ""
    tts_engine: TTSEngine = TTSEngine.QWEN
    voice_design_prompt: str | None = None  # For Qwen-TTS VoiceDesign
    voice_preset_id: int | None = None  # Voice preset for TTS
    speed_multiplier: float = 1.0
    include_scene_text: bool = True
    scene_text_font: str | None = None
    overlay_settings: OverlaySettings | None = None
    post_card_settings: PostCardSettings | None = None
    audio_ducking: bool = True
    bgm_volume: float = 0.4
    ducking_threshold: float = 0.01
    bgm_mode: str = "manual"  # "manual" | "auto"
    music_preset_id: int | None = None  # Music Preset (bgm_mode="manual")
    bgm_prompt: str | None = None  # Sound Designer prompt (bgm_mode="auto")


class VideoDeleteRequest(BaseModel):
    filename: str | None = None
    asset_id: int | None = None  # Preferred: delete by asset ID


class SceneGenerateRequest(BaseModel):
    prompt: str = Field(max_length=4000)
    negative_prompt: str = Field(default="", max_length=2000)
    steps: int = SD_DEFAULT_STEPS
    cfg_scale: float = SD_DEFAULT_CFG_SCALE
    sampler_name: str = SD_DEFAULT_SAMPLER
    seed: int = -1
    width: int = SD_DEFAULT_WIDTH
    height: int = SD_DEFAULT_HEIGHT
    clip_skip: int = 2
    enable_hr: bool = False
    hr_scale: float = 1.5
    hr_upscaler: str = "R-ESRGAN 4x+ Anime6B"
    hr_second_pass_steps: int = 10
    denoising_strength: float = 0.35
    # V3 Character Integration (optional for Narrator scenes)
    character_id: int | None = None
    character_b_id: int | None = None  # Multi-character: second character
    # Storyboard Integration (for Style Profile lookup)
    storyboard_id: int | None = None
    # Style LoRAs — ignored by backend; resolved from DB (SSOT). Kept for backward compat.
    style_loras: list[dict] | None = None
    # ControlNet options
    use_controlnet: bool = False
    controlnet_pose: str | None = None  # Specific pose name or None for auto-detect
    controlnet_weight: float = 1.0
    controlnet_control_mode: str = (
        "Balanced"  # "Balanced" | "My prompt is more important" | "ControlNet is more important"
    )
    # IP-Adapter options
    use_ip_adapter: bool = False
    ip_adapter_reference: str | None = None  # character_key for saved reference
    ip_adapter_weight: float = 0.7
    # Consistency Enhancements
    use_reference_only: bool = True  # Default to True if character_id exists
    reference_only_weight: float = 0.5
    environment_reference_id: int | None = None  # For Environment Pinning
    environment_reference_weight: float = 0.3
    # Background asset reference (auto-inject tags + Reference AdaIN atmosphere)
    background_id: int | None = None
    # Scene DB ID for character_actions lookup during V3 composition
    scene_id: int | None = None
    # Explicit V3 composition flag (True when frontend /prompt/compose already ran V3)
    # DEPRECATED: Frontend should send raw prompt + context_tags instead.
    prompt_pre_composed: bool = False
    # Scene context tags (expression, pose, gaze, camera, environment, mood)
    # Backend merges these into V3 composition automatically.
    context_tags: dict | None = None
    # Post-processing toggles (wired from frontend OPTIONS panel)
    auto_rewrite_prompt: bool = False
    auto_replace_risky_tags: bool = False
    # Warnings field to return messages from backend
    warnings: list[str] | None = None
    # Stable fallback for stale scene_id resolution
    client_id: str | None = None


class BatchSceneRequest(BaseModel):
    scenes: list[SceneGenerateRequest]


class SceneGenerateResponse(BaseModel):
    """Single scene generation result from SD WebUI."""

    image: str  # Base64 encoded PNG
    images: list[str] = []
    seed: int | None = None  # Actual seed used by SD API
    controlnet_pose: str | None = None
    ip_adapter_reference: str | None = None
    warnings: list[str] = []
    used_prompt: str | None = None


class BatchSceneResult(BaseModel):
    index: int
    status: Literal["success", "failed"]
    data: SceneGenerateResponse | None = None
    error: str | None = None


class BatchSceneResponse(BaseModel):
    results: list[BatchSceneResult]
    total: int
    succeeded: int
    failed: int


class SceneValidateRequest(BaseModel):
    """Validate scene image (WD14). Either image_b64 or image_url must be provided."""

    image_b64: str | None = None  # Data URL or raw base64
    image_url: str | None = None  # HTTP URL (backend fetches)
    prompt: str = ""
    # Analytics tracking
    storyboard_id: int | None = None
    scene_id: int | None = None  # Scene DB ID
    topic: str | None = None  # Optional: Content topic for reference
    scene_index: int | None = None  # Optional: Scene number (순서)
    character_id: int | None = None  # For identity_score calculation

    @model_validator(mode="after")
    def require_image_source(self):
        if not self.image_b64 and not self.image_url:
            raise ValueError("Either image_b64 or image_url must be provided")
        return self


class ImageStoreRequest(BaseModel):
    image_b64: str
    project_id: int
    group_id: int
    storyboard_id: int
    scene_id: int
    client_id: str | None = None  # Stable fallback when scene_id is stale after PUT
    file_name: str | None = None


class PromptRewriteRequest(BaseModel):
    base_prompt: str
    scene_prompt: str
    style: str = "Anime"
    mode: str = "compose"


class PromptSplitRequest(BaseModel):
    example_prompt: str
    style: str = "Anime"


class PromptComposeLoRA(BaseModel):
    """LoRA info for prompt composition."""

    name: str
    weight: float = 0.5
    trigger_words: list[str] | None = None
    lora_type: str | None = None  # character, style, concept
    optimal_weight: float | None = None
    calibration_score: int | None = None


class PromptComposeRequest(BaseModel):
    """Request for composing a prompt via V3 engine."""

    tokens: list[str]  # Raw prompt tokens
    mode: Literal["auto", "standard", "lora"] = "auto"
    loras: list[PromptComposeLoRA] | None = None
    use_break: bool = True  # Insert BREAK token
    # V3 extension fields
    character_id: int  # required — character tags/LoRAs loaded from DB
    character_b_id: int | None = None  # Multi-character: second character
    storyboard_id: int | None = None  # for resolving style LoRAs from DB (SSOT)
    scene_id: int | None = None  # for scene_mode validation (multi-char guard)
    context_tags: dict | None = None  # scene.context_tags
    background_id: int | None = None  # Stage BG → inject location tags into composition


class NegativeSource(BaseModel):
    """Origin of negative prompt tokens."""

    source: str  # "style_profile" | "character:<name>" | "scene"
    tokens: list[str]


class NegativePreviewRequest(BaseModel):
    """Request for negative prompt preview (lightweight, no character_id required)."""

    storyboard_id: int | None = None
    character_id: int | None = None
    character_b_id: int | None = None
    scene_id: int | None = None


class NegativePreviewResponse(BaseModel):
    """Response from negative prompt preview."""

    negative_prompt: str
    negative_sources: list[NegativeSource]


class ComposedLayer(BaseModel):
    """Single layer breakdown from 12-layer composition."""

    index: int
    name: str
    tokens: list[str]


class PromptComposeResponse(BaseModel):
    """Response from prompt composition."""

    prompt: str  # Final composed prompt string
    tokens: list[str]  # Ordered token list
    scene_complexity: str  # simple, moderate, complex
    lora_weights: dict[str, float] | None = None  # Calculated weights per LoRA
    meta: dict | None = None  # Additional metadata
    negative_prompt: str | None = None  # Composed final negative string
    negative_sources: list[NegativeSource] | None = None  # Per-source token breakdown
    layers: list[ComposedLayer] | None = None  # 12-layer breakdown (None for multi-char)


class TranslateKoRequest(BaseModel):
    """Request for KO → EN prompt translation."""

    ko_text: str = Field(max_length=2000)
    current_prompt: str | None = Field(default=None, max_length=5000)
    character_id: int | None = None


class TranslateKoResponse(BaseModel):
    """Response from KO → EN prompt translation."""

    translated_prompt: str
    source_ko: str


class EditPromptRequest(BaseModel):
    """Request for instruction-based prompt editing."""

    current_prompt: str = Field(max_length=5000)
    instruction: str = Field(max_length=2000)
    character_id: int | None = None


class EditPromptResponse(BaseModel):
    """Response from instruction-based prompt editing."""

    edited_prompt: str


class SDModelRequest(BaseModel):
    sd_model_checkpoint: str


# ============================================================
# Phase 6: Tag/LoRA/Character CRUD Schemas
# ============================================================


class TagBase(BaseModel):
    name: str = Field(max_length=100)
    ko_name: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    group_name: str | None = Field(default=None, max_length=50)
    priority: int = 100
    default_layer: int = 0
    usage_scope: str = "ANY"
    wd14_count: int = 0
    wd14_category: int = 0
    classification_source: str | None = None
    classification_confidence: float | None = None
    is_active: bool = True
    deprecated_reason: str | None = None
    replacement_tag_id: int | None = None


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    ko_name: str | None = Field(default=None, max_length=100)
    default_layer: int | None = None
    usage_scope: str | None = None


class TagResponse(TagBase):
    id: int
    thumbnail_url: str | None = None  # Response-only: derived from @property

    model_config = ConfigDict(from_attributes=True)


class TagSearchResponse(TagResponse):
    """Extended tag response for search with replacement info."""

    replacement_tag_name: str | None = None


class LoRABase(BaseModel):
    name: str = Field(max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    lora_type: str | None = None  # character, style, pose
    base_model: str | None = None  # SD1.5, SDXL, etc.
    trigger_words: list[str] | None = None
    default_weight: float = 0.7
    optimal_weight: float | None = None
    calibration_score: int | None = None
    weight_min: float = 0.1
    weight_max: float = 1.0
    gender_locked: str | None = None
    civitai_id: int | None = None
    civitai_url: str | None = None
    # Multi-Character Support
    is_multi_character_capable: bool = False
    multi_char_weight_scale: float | None = None
    multi_char_trigger_prompt: str | None = None
    # preview_image_url removed - now read-only @property via preview_image_asset


class LoRACreate(LoRABase):
    pass


class LoRAUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    lora_type: str | None = None
    base_model: str | None = None  # SD1.5, SDXL, etc.
    trigger_words: list[str] | None = None
    default_weight: float | None = None
    optimal_weight: float | None = None
    calibration_score: int | None = None
    weight_min: float | None = None
    weight_max: float | None = None
    gender_locked: Literal["female", "male"] | None = None
    # Multi-Character Support
    is_multi_character_capable: bool | None = None
    multi_char_weight_scale: float | None = None
    multi_char_trigger_prompt: str | None = None
    # preview_image_url removed - now read-only @property via preview_image_asset


class LoRAResponse(LoRABase):
    id: int
    preview_image_url: str | None = None  # Read-only from @property

    model_config = ConfigDict(from_attributes=True)


class CharacterTagLink(BaseModel):
    tag_id: int
    name: str | None = None  # Tag name for display
    group_name: str | None = None  # Tag group_name for wizard category
    layer: int | None = None  # Tag default_layer
    weight: float = 1.0
    is_permanent: bool = True


class CharacterBase(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    gender: str | None = None
    style_profile_id: int | None = None
    loras: list[CharacterLoRA] | None = None
    recommended_negative: list[str] | None = None
    custom_base_prompt: str | None = Field(default=None, max_length=10000)
    custom_negative_prompt: str | None = Field(default=None, max_length=10000)
    reference_base_prompt: str | None = Field(default=None, max_length=10000)
    reference_negative_prompt: str | None = Field(default=None, max_length=10000)
    # preview_image_url removed - now read-only @property via preview_image_asset
    # CharacterResponse gets it automatically via from_attributes=True from ORM model
    ip_adapter_weight: float | None = None
    ip_adapter_model: str | None = None
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None
    # Multi-angle references: [{"angle": "front", "asset_id": 123}, ...]
    reference_images: list[dict] | None = None
    preview_locked: bool = False
    voice_preset_id: int | None = None


class CharacterCreate(CharacterBase):
    tags: list[CharacterTagLink] | None = None
    # Legacy support (will be migrated to tags in router)
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    gender: str | None = None
    style_profile_id: int | None = None
    loras: list[CharacterLoRA] | None = None
    recommended_negative: list[str] | None = None
    custom_base_prompt: str | None = Field(default=None, max_length=10000)
    custom_negative_prompt: str | None = Field(default=None, max_length=10000)
    reference_base_prompt: str | None = Field(default=None, max_length=10000)
    reference_negative_prompt: str | None = Field(default=None, max_length=10000)
    # preview_image_url removed - now read-only @property via preview_image_asset
    ip_adapter_weight: float | None = None
    ip_adapter_model: str | None = None
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None
    reference_images: list[dict] | None = None
    preview_locked: bool | None = None
    voice_preset_id: int | None = None
    tags: list[CharacterTagLink] | None = None
    # Legacy support (will be migrated to tags in router)
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None


class CharacterResponse(CharacterBase):
    id: int
    tags: list[CharacterTagLink] = []
    style_profile_name: str | None = None  # Derived from style_profile relationship
    preview_image_asset_id: int | None = None
    preview_image_url: str | None = None  # Read-only from @property
    preview_key: str | None = None  # Read-only from @property (storage key)
    preview_locked: bool = False
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CharacterPreviewRequest(BaseModel):
    """Wizard preview: generate temp image without DB save."""

    gender: str = "female"
    tag_ids: list[int] = []
    loras: list[CharacterLoRA] | None = None
    style_profile_id: int | None = None
    controlnet_pose: str | None = None  # Pose name (default: config SD_REFERENCE_CONTROLNET_POSE)
    num_candidates: int = Field(default=1, ge=1, le=5)  # Number of candidates to generate


class CandidateImage(BaseModel):
    """Single candidate image from multi-candidate generation."""

    image: str  # Base64 PNG
    seed: int


class CharacterPreviewResponse(BaseModel):
    """Response-only: temp preview image data."""

    image: str  # Base64 PNG (first candidate, backward compat)
    used_prompt: str
    seed: int  # First candidate seed (backward compat)
    candidates: list[CandidateImage] = []  # All candidates
    warnings: list[str] = []


class RegenerateReferenceRequest(BaseModel):
    """Optional body for regenerate-reference endpoint."""

    controlnet_pose: str | None = None
    num_candidates: int = Field(default=1, ge=1, le=5)


class RegenerateReferenceResponse(BaseModel):
    """Response for POST /characters/{id}/regenerate-reference."""

    ok: bool
    url: str | None = None
    candidates: list[CandidateImage] = []


class AssignPreviewRequest(BaseModel):
    """Assign wizard-generated preview to saved character."""

    image_base64: str = Field(max_length=10_000_000)  # Raw base64, ~7.5 MB decoded limit


class AssignPreviewResponse(BaseModel):
    preview_image_url: str
    asset_id: int


# ============================================================
# SD Model Schemas
# ============================================================


class SDModelBase(BaseModel):
    name: str
    display_name: str | None = None
    model_type: str = "checkpoint"
    base_model: str | None = None
    civitai_id: int | None = None
    civitai_url: str | None = None
    description: str | None = None
    # preview_image_url removed - now read-only @property via preview_image_asset
    is_active: bool = True


class SDModelCreate(SDModelBase):
    pass


class SDModelUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    model_type: str | None = None
    base_model: str | None = None
    civitai_id: int | None = None
    civitai_url: str | None = None
    description: str | None = None
    # preview_image_url removed - now read-only @property via preview_image_asset
    is_active: bool | None = None


class SDModelResponse(SDModelBase):
    id: int
    preview_image_url: str | None = None  # Read-only from @property

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Embedding Schemas
# ============================================================


class EmbeddingBase(BaseModel):
    name: str
    display_name: str | None = None
    embedding_type: str = "negative"
    trigger_word: str | None = None
    base_model: str | None = None  # SD1.5, SDXL, etc.
    description: str | None = None
    is_active: bool = True


class EmbeddingCreate(EmbeddingBase):
    pass


class EmbeddingUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    embedding_type: str | None = None
    trigger_word: str | None = None
    base_model: str | None = None  # SD1.5, SDXL, etc.
    description: str | None = None
    is_active: bool | None = None


class EmbeddingResponse(EmbeddingBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Style Profile Schemas
# ============================================================


class LoRAWeight(BaseModel):
    lora_id: int
    weight: float = 1.0


class StyleProfileBase(BaseModel):
    name: str = Field(max_length=100)
    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sd_model_id: int | None = None
    loras: list[LoRAWeight] | None = None
    negative_embeddings: list[int] | None = None
    positive_embeddings: list[int] | None = None
    default_positive: str | None = None
    default_negative: str | None = None
    default_steps: int | None = None
    default_cfg_scale: float | None = None
    default_sampler_name: str | None = None
    default_clip_skip: int | None = None
    default_enable_hr: bool | None = None
    is_default: bool = False
    is_active: bool = True


class StyleProfileCreate(StyleProfileBase):
    pass


class StyleProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sd_model_id: int | None = None
    loras: list[LoRAWeight] | None = None
    negative_embeddings: list[int] | None = None
    positive_embeddings: list[int] | None = None
    default_positive: str | None = None
    default_negative: str | None = None
    default_steps: int | None = None
    default_cfg_scale: float | None = None
    default_sampler_name: str | None = None
    default_clip_skip: int | None = None
    default_enable_hr: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class StyleProfileResponse(StyleProfileBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SDModelBrief(BaseModel):
    id: int
    name: str
    display_name: str | None = None


class LoRABrief(BaseModel):
    id: int
    name: str
    display_name: str | None = None
    trigger_words: list[str] | None = None
    weight: float = 1.0


class EmbeddingBrief(BaseModel):
    id: int
    name: str
    trigger_word: str | None = None


class StyleProfileFullResponse(BaseModel):
    id: int
    name: str
    display_name: str | None = None
    description: str | None = None
    sd_model: SDModelBrief | None = None
    loras: list[LoRABrief] = []
    negative_embeddings: list[EmbeddingBrief] = []
    positive_embeddings: list[EmbeddingBrief] = []
    default_positive: str | None = None
    default_negative: str | None = None
    default_steps: int | None = None
    default_cfg_scale: float | None = None
    default_sampler_name: str | None = None
    default_clip_skip: int | None = None
    default_enable_hr: bool | None = None
    default_ip_adapter_model: str | None = None
    is_default: bool = False
    is_active: bool = True


class StyleProfileDeleteResponse(BaseModel):
    ok: bool
    deleted: str


# ============================================================
# Activity Log Schemas (Unified Memory)
# ============================================================


class ActivityLogBase(BaseModel):
    storyboard_id: int
    scene_id: int | None = None
    character_id: int | None = None
    prompt: str
    negative_prompt: str | None = None
    sd_params: dict | None = None
    seed: int | None = None
    # Input→media_asset_id on create; Response→derived from @property
    image_url: str | None = None
    match_rate: float | None = None
    tags_used: list[str] | None = None


class ActivityLogCreate(ActivityLogBase):
    pass


class ActivityLogUpdate(BaseModel):
    pass  # No updateable fields currently


class ActivityLogResponse(ActivityLogBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Gemini Image Editing
EditType = Literal["pose", "expression", "gaze", "framing", "hands"]


class GeminiEditRequest(BaseModel):
    """Gemini Nano Banana 이미지 편집 요청"""

    image_url: str | None = None  # Image URL (will be fetched by backend)
    image_b64: str | None = None  # Base64 encoded image (alternative)
    original_prompt: str  # 원본 프롬프트
    target_change: str  # 목표 변경사항 (예: "sitting on chair")
    edit_type: EditType | None = None  # 자동 감지 시 None


class GeminiEditResponse(BaseModel):
    """Gemini Nano Banana 이미지 편집 응답"""

    edited_image: str  # Base64 encoded edited image
    cost_usd: float  # 비용 ($)
    edit_type: EditType  # 적용된 편집 타입
    analysis: dict | None = None  # Vision 분석 결과 (선택)


class GeminiEditSuggestion(BaseModel):
    """개별 편집 제안"""

    issue: str  # 문제점 (예: "포즈 불일치")
    description: str  # 상세 설명
    target_change: str  # 제안된 변경사항
    confidence: float  # 신뢰도 (0.0~1.0)
    edit_type: EditType  # 편집 타입


class GeminiSuggestRequest(BaseModel):
    """Gemini 자동 제안 요청"""

    image_url: str | None = None  # Image URL (will be fetched by backend)
    image_b64: str | None = None  # Base64 encoded image (alternative)
    original_prompt: str  # 한국어 프롬프트


class GeminiSuggestResponse(BaseModel):
    """Gemini 자동 제안 응답"""

    has_mismatch: bool  # 불일치 발견 여부
    suggestions: list[GeminiEditSuggestion]  # 제안 목록
    cost_usd: float  # 비용 ($)


# --- Prompt History ---


class PromptHistoryBase(BaseModel):
    name: str | None = None
    positive_prompt: str
    negative_prompt: str | None = None
    steps: int = 20
    cfg_scale: float = 7.0
    sampler_name: str | None = None
    seed: int | None = None
    clip_skip: int = 2
    lora_settings: list[dict] | None = None
    context_tags: list[str] | None = None
    character_id: int | None = None


class PromptHistoryCreate(PromptHistoryBase):
    pass


class PromptHistoryUpdate(BaseModel):
    name: str | None = None
    is_favorite: bool | None = None


class PromptHistoryResponse(PromptHistoryBase):
    id: int
    is_favorite: bool
    use_count: int
    last_match_rate: float | None = None
    avg_match_rate: float | None = None
    validation_count: int
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PromptHistoryApplyResponse(BaseModel):
    id: int
    positive_prompt: str
    negative_prompt: str | None = None
    steps: int
    cfg_scale: float
    sampler_name: str | None = None
    seed: int | None = None
    clip_skip: int
    lora_settings: list[dict] | None = None
    context_tags: list[str] | None = None
    use_count: int


# ============================================================
# Voice Preset Schemas
# ============================================================


class VoicePresetCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    source_type: str = "generated"
    voice_design_prompt: str | None = Field(default=None, max_length=5000)
    voice_seed: int | None = None
    language: str = "korean"
    sample_text: str | None = None


class VoicePresetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    voice_design_prompt: str | None = Field(default=None, max_length=5000)


class VoicePreviewRequest(BaseModel):
    voice_design_prompt: str
    sample_text: str = "안녕하세요, 이것은 테스트 음성입니다."
    language: str = "korean"


class VoicePresetResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    source_type: str
    audio_url: str | None = None
    voice_design_prompt: str | None = None
    voice_seed: int | None = None
    language: str
    sample_text: str | None = None
    is_system: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Music Preset Schemas
# ============================================================


class MusicPresetCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    prompt: str | None = Field(default=None, max_length=5000)
    duration: float = 30.0
    seed: int | None = None


class MusicPresetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    prompt: str | None = Field(default=None, max_length=5000)
    duration: float | None = None
    seed: int | None = None


class MusicPresetResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    prompt: str | None = None
    duration: float | None = None
    seed: int | None = None
    audio_url: str | None = None
    is_system: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MusicPreviewRequest(BaseModel):
    prompt: str
    duration: float = 30.0
    seed: int = -1


# ============================================================
# Background Schemas
# ============================================================


class BackgroundCreate(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    weight: float = 0.3
    storyboard_id: int | None = None
    location_key: str | None = None


class BackgroundUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    weight: float | None = None
    location_key: str | None = None


class BackgroundResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    image_url: str | None = None  # Response-only: derived from @property
    image_asset_id: int | None = None
    tags: list[str] | None = None
    category: str | None = None
    weight: float
    is_system: bool
    storyboard_id: int | None = None
    location_key: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# YouTube Schemas
# ============================================================


class YouTubeAuthURLResponse(BaseModel):
    auth_url: str


class YouTubeCredentialResponse(BaseModel):
    project_id: int
    channel_id: str | None = None
    channel_title: str | None = None
    is_valid: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class YouTubeUploadRequest(BaseModel):
    project_id: int
    render_history_id: int
    title: str
    description: str = ""
    tags: list[str] = []
    privacy_status: str = "private"


class YouTubeUploadStatusResponse(BaseModel):
    render_history_id: int
    youtube_video_id: str | None = None
    youtube_upload_status: str | None = None
    youtube_uploaded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class YouTubeStatusesRequest(BaseModel):
    video_urls: list[str]


class YouTubeStatusEntry(BaseModel):
    video_id: str
    status: str | None = None


class YouTubeStatusesResponse(BaseModel):
    statuses: dict[str, YouTubeStatusEntry]


class RenderHistoryLookupResponse(BaseModel):
    render_history_id: int


class YouTubeRevokeResponse(BaseModel):
    status: str


# ============================================================
# Render Progress (SSE) Schemas
# ============================================================


class VideoCreateAccepted(BaseModel):
    """202 response for async video creation."""

    task_id: str


class ImageGenAccepted(BaseModel):
    """202 response for async image generation."""

    task_id: str


class ImageProgressEvent(BaseModel):
    """SSE event payload for image generation progress."""

    task_id: str
    stage: str
    percent: int = 0
    message: str = ""
    preview_image: str | None = None  # Base64 preview during generation
    image: str | None = None  # Base64 result on completion
    used_prompt: str | None = None
    warnings: list[str] = []
    error: str | None = None
    controlnet_pose: str | None = None
    ip_adapter_reference: str | None = None
    retry_count: int = 0
    retry_reason: str | None = None
    image_url: str | None = None  # Backend autonomous storage URL
    image_asset_id: int | None = None  # Saved MediaAsset ID


class SceneEditImageRequest(BaseModel):
    """Request for natural-language scene image editing."""

    edit_instruction: str  # 자연어 편집 지시 (예: "머리를 풀어헤치고 미소짓게")
    image_url: str | None = None  # 현재 이미지 URL (Backend가 fetch)
    image_b64: str | None = None  # 또는 Base64 이미지
    original_prompt: str | None = None  # 원본 프롬프트 (Optional, DB에서 조회)


class SceneEditImageResponse(BaseModel):
    """Response for scene image editing."""

    ok: bool
    edited_image: str | None = None  # Base64 편집된 이미지
    image_url: str | None = None  # Response-only: 저장된 이미지 URL
    asset_id: int | None = None
    cost_usd: float = 0.0
    edit_type: str | None = None


class TextExtractRequest(BaseModel):
    """Request body for caption/hashtag extraction endpoints."""

    text: str = Field(max_length=5000)


class CaptionExtractResponse(BaseModel):
    """Response for extract-caption endpoint."""

    caption: str
    original_length: int | None = None
    fallback: bool | None = None


class HashtagExtractResponse(BaseModel):
    """Response for extract-hashtags endpoint."""

    caption: str
    original_topic: str | None = None
    fallback: bool | None = None


class RenderProgressEvent(BaseModel):
    """SSE event payload for render progress."""

    task_id: str
    stage: str
    percent: int = 0
    message: str = ""
    encode_percent: int = 0
    current_scene: int = 0
    total_scenes: int = 0
    elapsed_seconds: float | None = None
    estimated_remaining_seconds: float | None = None
    video_url: str | None = None
    media_asset_id: int | None = None
    render_history_id: int | None = None
    error: str | None = None


# ── Storyboard Presets ─────────────────────────────────────────


class LanguageOption(BaseModel):
    value: str
    label: str


class PresetSummary(BaseModel):
    id: str
    name: str
    name_ko: str
    description: str
    structure: str
    sample_topics: list[str]
    default_duration: int
    default_style: str
    default_language: str


class PresetDetailResponse(BaseModel):
    id: str
    name: str
    name_ko: str
    description: str
    structure: str
    template: str
    sample_topics: list[str]
    default_duration: int
    default_style: str
    default_language: str
    extra_fields: dict


class ReadingSpeedConfig(BaseModel):
    """Reading speed config for a single language."""

    cps: float | None = None  # characters per second (Korean, Japanese)
    wps: float | None = None  # words per second (English)
    unit: str  # "chars" or "words"


class GenerationDefaults(BaseModel):
    """Per-scene generation flag defaults (SSOT from config.py)."""

    use_controlnet: bool = DEFAULT_USE_CONTROLNET
    controlnet_weight: float = DEFAULT_CONTROLNET_WEIGHT
    use_ip_adapter: bool = DEFAULT_USE_IP_ADAPTER
    ip_adapter_weight: float = DEFAULT_IP_ADAPTER_WEIGHT
    multi_gen_enabled: bool = DEFAULT_MULTI_GEN_ENABLED


class PresetListResponse(BaseModel):
    presets: list[PresetSummary]
    languages: list[LanguageOption]
    durations: list[int]
    reading_speed: dict[str, ReadingSpeedConfig] = {}
    optional_steps: list[str] = []
    generation_defaults: GenerationDefaults | None = None


class PresetTopicsResponse(BaseModel):
    topics: list[str]


# ============================================================
# Script Generate Schemas
# ============================================================


class ScriptGenerateSceneItem(BaseModel):
    script: str = ""
    speaker: str = "Narrator"
    duration: float = 3.0
    image_prompt: str = ""
    image_prompt_ko: str = ""
    negative_prompt: str | None = None
    context_tags: dict | None = None


class SoundRecommendation(BaseModel):
    """Sound Designer 추천 결과."""

    prompt: str | None = None
    mood: str | None = None
    duration: float | None = None


class ScriptGenerateResponse(BaseModel):
    scenes: list[ScriptGenerateSceneItem]
    character_id: int | None = None
    character_b_id: int | None = None
    sound_recommendation: SoundRecommendation | None = None


class ScriptProgressEvent(BaseModel):
    """SSE 스트리밍 진행률 이벤트 (문서화용)."""

    node: str
    label: str
    percent: int
    status: str  # "running" | "completed" | "error" | "waiting_for_input"
    node_result: dict | None = None
    result: ScriptGenerateResponse | None = None
    error: str | None = None


class SceneReasoningItem(BaseModel):
    """씬별 창작 근거."""

    narrative_function: str = ""
    why: str = ""
    alternatives: list[str] = Field(default_factory=list)


class ScriptResumeRequest(BaseModel):
    """Human Gate / Concept Gate 재개 요청."""

    thread_id: str
    action: str = "approve"  # "approve"|"revise"|"select"|"regenerate"|"custom_concept"
    feedback: str | None = None
    concept_id: int | None = None  # concept_gate용: 선택한 컨셉 인덱스 (0-2)
    feedback_preset: str | None = None  # 피드백 프리셋 ID
    feedback_preset_params: dict[str, str] | None = None  # 프리셋 파라미터
    custom_concept: dict | None = None  # 사용자 직접 입력 컨셉
    trace_id: str | None = None  # Langfuse trace 연결용 (generate 시 받은 값)


class ScriptPresetItem(BaseModel):
    """Preset 목록 아이템."""

    id: str
    name: str
    name_ko: str
    description: str
    auto_approve: bool = False
    skip_stages: list[str] = []


class ScriptPresetsResponse(BaseModel):
    """Preset 목록 응답."""

    presets: list[ScriptPresetItem]


class FeedbackPresetOption(BaseModel):
    """개별 피드백 프리셋."""

    id: str
    label: str
    icon: str
    feedback: str
    has_params: bool = False
    param_options: dict[str, list[str]] | None = None


class FeedbackPresetsResponse(BaseModel):
    """피드백 프리셋 목록 응답."""

    presets: list[FeedbackPresetOption]


# ============================================================
# Script Feedback Schemas
# ============================================================


class ScriptFeedbackRequest(BaseModel):
    thread_id: str
    storyboard_id: int | None = None
    rating: Literal["positive", "negative"]
    feedback_text: str | None = None


class ScriptFeedbackResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Materials Check Schemas
# ============================================================


class VerticalStatus(BaseModel):
    ready: bool = False
    count: int | None = None
    detail: str | None = None


class MaterialsCheckResponse(BaseModel):
    storyboard_id: int
    script: VerticalStatus
    characters: VerticalStatus
    voice: VerticalStatus
    music: VerticalStatus
    background: VerticalStatus


# ============================================================
# Generic / Shared Response Schemas
# ============================================================


class PaginatedStoryboardList(BaseModel):
    """Paginated response for GET /storyboards."""

    items: list[StoryboardListItem]
    total: int
    offset: int = 0
    limit: int = 50


class PaginatedCharacterList(BaseModel):
    """Paginated response for GET /characters."""

    items: list[CharacterResponse]
    total: int
    offset: int = 0
    limit: int = 50


class RenderHistoryItem(BaseModel):
    """Single item in the render history gallery."""

    id: int
    label: str
    url: str  # Response-only: derived from media_asset.url
    created_at: datetime
    storyboard_id: int
    storyboard_title: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    group_id: int | None = None
    group_name: str | None = None


class PaginatedRenderHistoryList(BaseModel):
    """Paginated response for GET /video/render-history."""

    items: list[RenderHistoryItem]
    total: int
    offset: int = 0
    limit: int = 12


class StatusResponse(BaseModel):
    """Generic status response for simple operations (delete, restore, etc)."""

    status: str


class TrashedStoryboardItem(BaseModel):
    """Item in the trashed storyboards list."""

    id: int
    title: str | None = None
    deleted_at: str | None = None


class StoryboardRestoreResponse(BaseModel):
    """Response for POST /storyboards/{id}/restore."""

    ok: bool
    restored: str | None = None


# ============================================================
# Seed Anchoring Schemas
# ============================================================


class SeedAnchorRequest(BaseModel):
    """Request for setting storyboard base_seed.

    base_seed: null → auto-generate, 0 → clear, positive → set explicitly.
    """

    base_seed: int | None = Field(default=None, ge=0)


class SeedAnchorResponse(BaseModel):
    """Response for seed anchoring operation."""

    storyboard_id: int
    base_seed: int | None = None
    anchored: bool = False


class ImageCacheStatsResponse(BaseModel):
    """Response for image cache stats."""

    enabled: bool = False
    file_count: int = 0
    total_size_mb: float = 0.0
    max_size_mb: int = 2048
    cache_dir: str = ""


class ImageCacheClearResponse(BaseModel):
    """Response for image cache clear."""

    cleared: int = 0


# ============================================================
# IP-Adapter Reference Schemas (ControlNet Router)
# ============================================================


class UploadPhotoReferenceRequest(BaseModel):
    character_key: str
    image_b64: str  # Real photo (will be face-cropped + resized)


class QualityInfo(BaseModel):
    """Quality info for upload responses."""

    valid: bool = False
    face_detected: bool = False
    face_count: int = 0
    face_size_ratio: float = 0.0
    warnings: list[str] = []


class UploadPhotoReferenceResponse(BaseModel):
    character_key: str
    filename: str | None = None
    success: bool = False
    error: str | None = None
    quality: QualityInfo | None = None  # Response-only: derived from ReferenceQualityReport


class ReferenceQualityResponse(BaseModel):
    character_key: str
    valid: bool = False
    face_detected: bool = False
    face_count: int = 0
    face_size_ratio: float = 0.0
    resolution_ok: bool = True
    width: int = 0
    height: int = 0
    warnings: list[str] = []


class ReferenceAngleInput(BaseModel):
    """Single angle reference for multi-angle upload."""

    angle: str  # "front" | "side_left" | "side_right" | "back"
    image_b64: str


class MultiReferenceRequest(BaseModel):
    character_key: str
    references: list[ReferenceAngleInput]


class MultiReferenceSaved(BaseModel):
    angle: str
    asset_id: int | None = None
    filename: str


class MultiReferenceResponse(BaseModel):
    character_key: str
    references: list[MultiReferenceSaved]


class ImageStoreResponse(BaseModel):
    """Response for POST /image/store."""

    url: str
    asset_id: int


class CriticalFailureItem(BaseModel):
    """Single critical failure detection result."""

    failure_type: str
    expected: str
    detected: str
    confidence: float


class CriticalFailureInfo(BaseModel):
    """Critical failure detection summary."""

    has_failure: bool
    failures: list[CriticalFailureItem] = []


class SceneValidationResponse(BaseModel):
    """Response for POST /scene/validate_image."""

    mode: str = "wd14"
    match_rate: float = 0.0
    adjusted_match_rate: float = 0.0
    matched: list[str] = []
    missing: list[str] = []
    extra: list[str] = []
    skipped: list[str] = []
    partial_matched: list[str] = []
    tags: list[str] = []
    critical_failure: CriticalFailureInfo | None = None
    identity_score: float | None = None


class VideoCreateResponse(BaseModel):
    """Response for POST /video/create (sync)."""

    video_url: str
    media_asset_id: int | None = None
    render_history_id: int | None = None


class VideoDeleteResponse(BaseModel):
    """Response for POST /video/delete."""

    ok: bool
    deleted: bool = False
    asset_id: int | None = None
    legacy: bool | None = None
    reason: str | None = None


class VideoExistsResponse(BaseModel):
    """Response for GET /video/exists."""

    exists: bool


class TransitionItem(BaseModel):
    """A scene transition effect."""

    value: str
    label: str
    description: str = ""
    visual: str = ""


class TransitionsResponse(BaseModel):
    """Response for GET /video/transitions."""

    transitions: list[TransitionItem]


# ============================================================
# Memory Store Schemas
# ============================================================


class MemoryItem(BaseModel):
    namespace: list[str]
    key: str
    value: dict
    created_at: str | None = None
    updated_at: str | None = None


class MemoryDeleteResponse(BaseModel):
    success: bool
    message: str


class MemoryListResponse(BaseModel):
    namespace: str
    items: list[MemoryItem]


class MemoryStatsResponse(BaseModel):
    total: int
    by_namespace: dict[str, int]


# ============================================================
# Cross-Scene Consistency (Phase 16-D)
# ============================================================


class GroupDriftResponse(BaseModel):
    group: str
    baseline_tags: list[str]
    detected_tags: list[str]
    status: str  # match | mismatch | missing | extra | no_data
    weight: float


class SceneDriftResponse(BaseModel):
    scene_id: int
    scene_order: int
    character_id: int
    identity_score: float
    drift_score: float
    groups: list[GroupDriftResponse]


class ConsistencyResponse(BaseModel):
    storyboard_id: int
    overall_consistency: float
    scenes: list[SceneDriftResponse]


# ============================================================
# Storyboard Create Response
# ============================================================


class StoryboardCreateResponse(BaseModel):
    """Response for POST /storyboards/create (Gemini script generation)."""

    scenes: list[dict]
    character_id: int | None = None
    character_b_id: int | None = None


# ============================================================
# Validate + Auto-Edit Response
# ============================================================


class ValidateAndAutoEditResponse(BaseModel):
    """Response for POST /scene/validate-and-auto-edit."""

    validation_result: dict
    auto_edit_triggered: bool = False
    edited_image: str | None = None
    edit_cost: float | None = None
    original_match_rate: float | None = None
    final_match_rate: float | None = None
    edit_type: str | None = None
    skip_reason: str | None = None
    current_cost: float | None = None
    retry_count: int | None = None
    auto_edit_error: str | None = None
    edit_log_id: int | None = None


# ============================================================
# Scene Cancel Response
# ============================================================


class SceneCancelResponse(BaseModel):
    """Response for POST /scene/cancel/{task_id}."""

    ok: bool
    reason: str | None = None


# ============================================================
# Phase 18: Stage Workflow Schemas
# ============================================================


class StageLocationResult(BaseModel):
    """Result for a single location background generation."""

    location_key: str
    background_id: int
    status: str  # "generated" | "exists" | "failed"


class StageGenerateResponse(BaseModel):
    """Response for POST /{storyboard_id}/stage/generate-backgrounds."""

    storyboard_id: int
    results: list[StageLocationResult]


class StageLocationStatus(BaseModel):
    """Status of a single location background."""

    location_key: str
    background_id: int | None = None
    image_url: str | None = None  # Response-only: derived from image_asset
    tags: list[str] = []
    scene_ids: list[int] = []
    has_image: bool = False
    style_profile_id: int | None = None  # Response-only: style used for generation


class StageStatusResponse(BaseModel):
    """Response for GET /{storyboard_id}/stage/status."""

    storyboard_id: int
    stage_status: str | None
    locations: list[StageLocationStatus]
    total: int
    ready: int


class StageAssignment(BaseModel):
    """A single scene-to-background assignment."""

    scene_id: int
    background_id: int
    location_key: str


class StageAssignResponse(BaseModel):
    """Response for POST /{storyboard_id}/stage/assign-backgrounds."""

    assignments: list[StageAssignment]


class StageRegenerateRequest(BaseModel):
    """Request body for POST /{storyboard_id}/stage/regenerate-background/{location_key}."""

    tags: list[str] | None = None  # If provided, update tags before regenerating


class StageRegenerateResponse(BaseModel):
    """Response for POST /{storyboard_id}/stage/regenerate-background/{location_key}."""

    background_id: int
    status: str  # "regenerated" | "failed"
