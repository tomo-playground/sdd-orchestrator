from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from config import (
    DEFAULT_CONTROLNET_WEIGHT,
    DEFAULT_ENABLE_HR,
    DEFAULT_ENVIRONMENT_REFERENCE_WEIGHT,
    DEFAULT_IP_ADAPTER_WEIGHT,
    DEFAULT_LANGUAGE,
    DEFAULT_LORA_WEIGHT,
    DEFAULT_MULTI_GEN_ENABLED,
    DEFAULT_PLATFORM,
    DEFAULT_REFERENCE_ONLY_WEIGHT,
    DEFAULT_SPEAKER,
    DEFAULT_STRUCTURE,
    DEFAULT_TONE,
    DEFAULT_TTS_ENGINE,
    DEFAULT_USE_CONTROLNET,
    DEFAULT_USE_IP_ADAPTER,
    SD_DEFAULT_CFG_SCALE,
    SD_DEFAULT_CLIP_SKIP,
    SD_DEFAULT_HEIGHT,
    SD_DEFAULT_SAMPLER,
    SD_DEFAULT_STEPS,
    SD_DEFAULT_WIDTH,
    SD_HI_RES_DENOISING_STRENGTH,
    SD_HI_RES_SCALE,
    SD_HI_RES_SECOND_PASS_STEPS,
    SD_HI_RES_UPSCALER,
    SUPPORTED_TTS_ENGINES,
    normalize_base_model,
)

logger = logging.getLogger(__name__)


class _BaseModelNormMixin(BaseModel):
    """Mixin: normalizes base_model field (e.g. 'SD 1.5' → 'SD1.5')."""

    @field_validator("base_model", mode="before", check_fields=False)
    @classmethod
    def _normalize_base_model(cls, v: str | None) -> str | None:
        return normalize_base_model(v)


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


class QuickStartRequest(BaseModel):
    project_name: str = Field(default="내 채널", max_length=100)
    group_name: str = Field(default="기본 시리즈", max_length=200)


class QuickStartResponse(BaseModel):
    project_id: int
    group_id: int
    style_profile_id: int | None = None
    message: str


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
    audio_ducking: bool | None = Field(default=None, validation_alias="audio_ducking")
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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
    character_count: int = 0
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupTrashItem(BaseModel):
    """Soft-deleted group item for trash listing."""

    id: int
    name: str
    deleted_at: datetime

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
    tone: str = DEFAULT_TONE
    duration: int | None = None
    language: str | None = None


class CastingRecommendationSchema(BaseModel):
    """Phase 20-C: AI casting recommendation persisted with storyboard."""

    character_a_id: int | None = None  # Speaker A 캐릭터 ID
    character_a_name: str = ""  # Speaker A 캐릭터 이름
    character_b_id: int | None = None  # Speaker B 캐릭터 ID
    character_b_name: str = ""  # Speaker B 캐릭터 이름
    structure: str | None = None
    reasoning: str = Field(default="", max_length=2000)


class StoryboardSave(StoryboardBase):
    character_id: int | None = None
    character_b_id: int | None = None
    version: int | None = None  # Optimistic locking: current version from client
    bgm_prompt: str | None = None  # Sound Designer recommendation.prompt
    bgm_mood: str | None = None  # Sound Designer recommendation.mood
    casting_recommendation: CastingRecommendationSchema | None = None
    scenes: list[StoryboardScene]
    used_story_card_ids: list[int] | None = None  # SP-075: 파이프라인에서 사용된 소재 카드 ID


class StoryboardDraftRequest(BaseModel):
    """POST /storyboards/draft -- 스크립트 생성 전 빈 스토리보드 확보."""

    title: str = Field(default="Draft", max_length=200)
    group_id: int


class StoryboardDraftResponse(BaseModel):
    """Response for POST /storyboards/draft."""

    storyboard_id: int
    title: str
    created: bool  # True=신규 생성, False=기존 반환 (멱등)


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
    created_at: int  # Millisecond timestamp
    render_history_id: int | None = None


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
    width: int = 832
    height: int = 1216
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
    tts_asset_id: int | None = None

    model_config = ConfigDict(populate_by_name=True)


class StoryboardCharacterResponse(BaseModel):
    """Character cast info for a storyboard."""

    speaker: str  # "speaker_1", "speaker_2"
    character_id: int
    character_name: str
    reference_image_url: str | None = None  # Response-only: derived from Character.reference_image_url


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


class ChatContextMessage(BaseModel):
    """사전 대화 이력 항목."""

    role: Literal["user", "assistant"] = "user"
    text: str = Field(default="", max_length=2000)


class StoryboardRequest(BaseModel):
    topic: str = Field(max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    duration: int = 10
    style: str = "Anime"
    language: str = DEFAULT_LANGUAGE
    structure: str = ""  # 빈값 = Director가 캐스팅 시 결정 (Frontend 미전달)
    tone: str = DEFAULT_TONE
    actor_a_gender: str = "female"
    character_id: int | None = None  # Director가 캐스팅 시 결정 (Frontend 미전달)
    character_b_id: int | None = None  # Director가 캐스팅 시 결정 (Frontend 미전달)
    group_id: int | None = None
    storyboard_id: int | None = None  # Draft storyboard ID (트레이싱/로깅용)
    preset: str | None = Field(default=None, json_schema_extra={"deprecated": True})
    skip_stages: list[str] | None = Field(default=None, json_schema_extra={"deprecated": True})
    references: list[str] | None = Field(default=None, max_length=5)  # URL 또는 텍스트 (최대 5개)
    selected_concept: dict | None = None  # Critic 선정 컨셉 (title, concept, strengths)
    interaction_mode: str = "guided"
    chat_context: list[ChatContextMessage] | None = Field(default=None, max_length=20)

    @field_validator("interaction_mode", mode="before")
    @classmethod
    def _coerce_interaction_mode(cls, v: str | None) -> str:
        from config import coerce_interaction_mode  # noqa: PLC0415

        return coerce_interaction_mode(v)


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
    width: int = 832
    height: int = 1216

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
    tts_asset_id: int | None = None

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


TTSEngine = Enum("TTSEngine", {v.upper(): v for v in SUPPORTED_TTS_ENGINES}, type=str)  # type: ignore[misc]


class _SceneEmotionCoerce:
    """scene_emotion 리스트→문자열 coerce mixin."""

    @field_validator("scene_emotion", mode="before")
    @classmethod
    def _coerce_scene_emotion(cls, v: object) -> str | None:
        if isinstance(v, list):
            return ", ".join(str(x) for x in v) if v else None
        return v  # type: ignore[return-value]


class VideoScene(_SceneEmotionCoerce, BaseModel):
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
    # English scene description for TTS voice context
    image_prompt: str | None = None
    # Korean scene description (for context-aware voice generation)
    image_prompt_ko: str | None = None
    # Linked TTS preview asset (skip TTS generation if valid)
    tts_asset_id: int | None = None
    # DB scene ID — used to persist resolved voice_design_prompt on first render
    scene_db_id: int | None = None

    model_config = ConfigDict(extra="allow")


class OverlaySettings(BaseModel):
    channel_name: str = "daily_shorts"
    avatar_key: str | None = None
    likes_count: str = "12.5k"
    posted_time: str = "2분 전"
    caption: str = "Amazing video! #shorts"
    frame_style: str = "overlay_minimal.png"
    avatar_file: str | None = None


class PostCardSettings(BaseModel):
    channel_name: str = "creator"
    avatar_key: str | None = None
    caption: str = ""


class VideoRequest(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_tts_engine(cls, values):
        if isinstance(values, dict):
            engine = values.get("tts_engine")
            if engine in ("edge", "sovits"):
                logger.warning("[TTS] tts_engine='%s' deprecated, auto-converting to 'qwen'", engine)
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
    tts_engine: TTSEngine = TTSEngine(DEFAULT_TTS_ENGINE)
    voice_design_prompt: str | None = None  # For Qwen-TTS VoiceDesign
    voice_preset_id: int | None = None  # Voice preset for TTS
    speed_multiplier: float = 1.0
    include_scene_text: bool = True
    scene_text_font: str | None = None
    overlay_settings: OverlaySettings | None = None
    post_card_settings: PostCardSettings | None = None
    audio_ducking: bool = True
    bgm_volume: float = 0.4
    ducking_threshold: float = 0.03
    bgm_mode: str = "manual"  # "manual" | "auto"
    music_preset_id: int | None = None  # Music Preset (bgm_mode="manual")
    bgm_prompt: str | None = None  # Sound Designer prompt (bgm_mode="auto")
    platform: str = DEFAULT_PLATFORM  # Target platform for safe zone calculation


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
    clip_skip: int = SD_DEFAULT_CLIP_SKIP
    enable_hr: bool = DEFAULT_ENABLE_HR
    hr_scale: float = SD_HI_RES_SCALE
    hr_upscaler: str = SD_HI_RES_UPSCALER
    hr_second_pass_steps: int = SD_HI_RES_SECOND_PASS_STEPS
    denoising_strength: float = SD_HI_RES_DENOISING_STRENGTH
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
    ip_adapter_weight: float = DEFAULT_IP_ADAPTER_WEIGHT
    # Consistency Enhancements
    use_reference_only: bool = True  # Default to True if character_id exists
    reference_only_weight: float = DEFAULT_REFERENCE_ONLY_WEIGHT
    environment_reference_id: int | None = None  # For Environment Pinning
    environment_reference_weight: float = DEFAULT_ENVIRONMENT_REFERENCE_WEIGHT
    # Background asset reference (auto-inject tags + Reference AdaIN atmosphere)
    background_id: int | None = None
    # Scene DB ID for character_actions lookup during prompt composition
    scene_id: int | None = None
    # Explicit prompt composition flag (True when frontend /prompt/compose already ran)
    # DEPRECATED: Frontend should send raw prompt + context_tags instead.
    prompt_pre_composed: bool = False
    # Scene context tags (expression, pose, gaze, camera, environment, mood)
    # Backend merges these into prompt composition automatically.
    context_tags: dict | None = None
    # ComfyUI workflow hint
    comfy_workflow: str | None = None
    # Post-processing toggles (wired from frontend OPTIONS panel)
    auto_rewrite_enabled: bool = False
    auto_replace_risky_tags: bool = False
    # Warnings field to return messages from backend
    warnings: list[str] | None = None
    # Stable fallback for stale scene_id resolution
    client_id: str | None = None


class SceneGenerateResponse(BaseModel):
    """Single scene generation result from SD WebUI."""

    image: str  # Base64 encoded PNG
    images: list[str] = []
    seed: int | None = None  # Actual seed used by SD API
    controlnet_pose: str | None = None
    ip_adapter_reference: str | None = None
    warnings: list[str] = []
    used_prompt: str | None = None
    used_negative_prompt: str | None = None
    used_steps: int | None = None
    used_cfg_scale: float | None = None
    used_sampler: str | None = None
    consistency_quality: str | None = None  # "high" | "medium" | "low"
    # WD14 validation results (populated after autonomous backend storage)
    match_rate: float | None = None
    matched_tags: list[str] | None = None
    missing_tags: list[str] | None = None


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


class PromptComposeRequest(BaseModel):
    """Request for composing a prompt via prompt composition engine."""

    tokens: list[str]  # Raw prompt tokens
    mode: Literal["auto", "standard", "lora"] = "auto"
    loras: list[PromptComposeLoRA] | None = None
    is_break_enabled: bool = True  # Insert BREAK token
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

    model_config = ConfigDict(from_attributes=True)


class TagSearchResponse(TagResponse):
    """Extended tag response for search with replacement info."""

    replacement_tag_name: str | None = None


class LoRABase(_BaseModelNormMixin):
    name: str = Field(max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    lora_type: str | None = None  # character, style, pose
    base_model: str | None = None  # SD1.5, SDXL, etc.
    trigger_words: list[str] | None = None
    default_weight: float = DEFAULT_LORA_WEIGHT
    weight_min: float = 0.1
    weight_max: float = 1.0
    civitai_url: str | None = None
    # preview_image_url removed - now read-only @property via preview_image_asset


class LoRACreate(LoRABase):
    pass


class LoRAUpdate(_BaseModelNormMixin):
    name: str | None = Field(default=None, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    lora_type: str | None = None
    base_model: str | None = None  # SD1.5, SDXL, etc.
    trigger_words: list[str] | None = None
    default_weight: float | None = None
    weight_min: float | None = None
    weight_max: float | None = None
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
    group_id: int
    loras: list[CharacterLoRA] | None = None
    positive_prompt: str | None = Field(default=None, max_length=10000)
    negative_prompt: str | None = Field(default=None, max_length=10000)
    # reference_image_url: read-only @property via reference_image_asset (CharacterResponse only)
    ip_adapter_weight: float | None = None
    ip_adapter_model: str | None = None
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None
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
    group_id: int | None = None
    loras: list[CharacterLoRA] | None = None
    positive_prompt: str | None = Field(default=None, max_length=10000)
    negative_prompt: str | None = Field(default=None, max_length=10000)
    ip_adapter_weight: float | None = None
    ip_adapter_model: str | None = None
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None
    voice_preset_id: int | None = None
    tags: list[CharacterTagLink] | None = None
    # Legacy support (will be migrated to tags in router)
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None


class CharacterResponse(CharacterBase):
    id: int
    tags: list[CharacterTagLink] = []
    group_name: str | None = None  # Derived from group relationship
    style_profile_name: str | None = None  # Derived from group.style_profile (2-hop)
    reference_image_asset_id: int | None = None
    reference_image_url: str | None = None  # Read-only from @property
    reference_key: str | None = None  # Read-only from @property (storage key)
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CharacterPreviewRequest(BaseModel):
    """Wizard preview: generate temp image without DB save."""

    gender: str = "female"
    tag_ids: list[int] = []
    loras: list[CharacterLoRA] | None = None
    style_profile_id: int | None = None  # Wizard-only: derived from selected group's style_profile_id
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


class CharacterDuplicateRequest(BaseModel):
    """Request to duplicate a character into a different group."""

    target_group_id: int
    new_name: str = Field(max_length=100)
    should_copy_loras: bool = False
    should_copy_reference: bool = False


class CharacterDuplicateResponse(BaseModel):
    id: int
    name: str
    group_id: int
    group_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AssignPreviewRequest(BaseModel):
    """Assign wizard-generated preview to saved character."""

    image_base64: str = Field(max_length=10_000_000)  # Raw base64, ~7.5 MB decoded limit


class AssignPreviewResponse(BaseModel):
    reference_image_url: str
    asset_id: int


# ============================================================
# SD Model Schemas
# ============================================================


class SDModelBase(_BaseModelNormMixin):
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


class SDModelUpdate(_BaseModelNormMixin):
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


class EmbeddingBase(_BaseModelNormMixin):
    name: str
    display_name: str | None = None
    embedding_type: str = "negative"
    trigger_word: str | None = None
    base_model: str | None = None  # SD1.5, SDXL, etc.
    description: str | None = None
    is_active: bool = True


class EmbeddingCreate(EmbeddingBase):
    pass


class EmbeddingUpdate(_BaseModelNormMixin):
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
    reference_env_tags: list[str] | None = None
    reference_camera_tags: list[str] | None = None
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
    reference_env_tags: list[str] | None = None
    reference_camera_tags: list[str] | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class StyleProfileResponse(StyleProfileBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SDModelBrief(BaseModel):
    id: int
    name: str
    display_name: str | None = None
    base_model: str | None = None


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
    reference_env_tags: list[str] | None = None
    reference_camera_tags: list[str] | None = None
    is_default: bool = False
    is_active: bool = True


class StyleProfileDeleteResponse(BaseModel):
    ok: bool
    deleted: str


# ============================================================
# Activity Log Schemas
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
    sample_text: str = "어느 날 문득, 익숙한 골목길에서 낯선 설렘을 느꼈다. 바람이 불어오는 방향으로 고개를 돌렸을 때, 그 사람이 서 있었다."
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
    used_negative_prompt: str | None = None
    used_steps: int | None = None
    used_cfg_scale: float | None = None
    used_sampler: str | None = None
    seed: int | None = None
    warnings: list[str] = []
    error: str | None = None
    controlnet_pose: str | None = None
    ip_adapter_reference: str | None = None
    retry_count: int = 0
    retry_reason: str | None = None
    image_url: str | None = None  # Backend autonomous storage URL
    image_asset_id: int | None = None  # Saved MediaAsset ID
    # WD14 validation results (populated after autonomous backend storage)
    match_rate: float | None = None
    matched_tags: list[str] | None = None
    missing_tags: list[str] | None = None


class TextExtractRequest(BaseModel):
    """Request body for caption/hashtag extraction endpoints."""

    text: str = Field(max_length=5000)


class CaptionExtractResponse(BaseModel):
    """Response for extract-caption endpoint."""

    caption: str
    original_length: int | None = None
    is_fallback: bool | None = None


class HashtagExtractResponse(BaseModel):
    """Response for extract-hashtags endpoint."""

    caption: str
    original_topic: str | None = None
    is_fallback: bool | None = None


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
    enable_hr: bool = DEFAULT_ENABLE_HR


class HiResDefaults(BaseModel):
    """Hi-Res Fix defaults (SSOT from config.py)."""

    scale: float = SD_HI_RES_SCALE
    upscaler: str = SD_HI_RES_UPSCALER
    second_pass_steps: int = SD_HI_RES_SECOND_PASS_STEPS
    denoising_strength: float = SD_HI_RES_DENOISING_STRENGTH


class ImageDefaults(BaseModel):
    """Image dimension defaults (SSOT from config.py)."""

    width: int = SD_DEFAULT_WIDTH
    height: int = SD_DEFAULT_HEIGHT


class StepMetadata(BaseModel):
    """Pipeline step metadata for Frontend display."""

    key: str
    label: str
    desc: str = ""


class ToneOption(BaseModel):
    id: str
    label: str
    label_ko: str


class EmotionPresetOption(BaseModel):
    id: str
    label: str
    emotion: str


class BgmMoodPresetOption(BaseModel):
    id: str
    label: str
    mood: str
    prompt: str


class IdLabelOption(BaseModel):
    id: str
    label: str


class PresetListResponse(BaseModel):
    presets: list[PresetSummary]
    languages: list[LanguageOption]
    tones: list[ToneOption] = []
    durations: list[int]
    reading_speed: dict[str, ReadingSpeedConfig] = {}
    optional_steps: list[str] = []
    pipeline_metadata: list[StepMetadata] = []
    generation_defaults: GenerationDefaults | None = None
    hi_res_defaults: HiResDefaults | None = None
    image_defaults: ImageDefaults | None = None
    samplers: list[str] = []
    tts_engine: str = DEFAULT_TTS_ENGINE
    tts_engines: list[str] = Field(default_factory=lambda: list(SUPPORTED_TTS_ENGINES))
    emotion_presets: list[EmotionPresetOption] = []
    bgm_mood_presets: list[BgmMoodPresetOption] = []
    ip_adapter_models: list[str] = []
    overlay_styles: list[IdLabelOption] = []


class PresetTopicsResponse(BaseModel):
    topics: list[str]


# ============================================================
# Script Generate Schemas
# ============================================================


class ScriptGenerateSceneItem(BaseModel):
    script: str = ""
    speaker: str = DEFAULT_SPEAKER
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
    structure: str | None = None
    character_id: int | None = None
    character_b_id: int | None = None
    sound_recommendation: SoundRecommendation | None = None
    warnings: list[str] | None = None


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


class IntakeResumeValue(BaseModel):
    """Intake 재개 시 사용자 선택값."""

    model_config = ConfigDict(extra="forbid")

    structure: str | None = None
    tone: str | None = None
    character_id: int | None = None
    character_b_id: int | None = None


class ScriptResumeRequest(BaseModel):
    """Human Gate / Concept Gate / Intake 재개 요청."""

    thread_id: str
    action: str = "approve"  # "approve"|"revise"|"select"|"regenerate"|"custom_concept"|"answer"
    feedback: str | None = None
    concept_id: int | None = None  # concept_gate용: 선택한 컨셉 인덱스 (0-2)
    feedback_preset: str | None = None  # 피드백 프리셋 ID
    feedback_preset_params: dict[str, str] | None = None  # 프리셋 파라미터
    custom_concept: dict | None = None  # 사용자 직접 입력 컨셉
    intake_value: IntakeResumeValue | None = None  # intake용
    trace_id: str | None = None  # Langfuse trace 연결용 (generate 시 받은 값)
    storyboard_id: int | None = None  # LangFuse session 연결용


class ScriptPresetItem(BaseModel):
    """Preset 목록 아이템."""

    id: str
    name: str
    name_ko: str
    description: str


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
    is_ready: bool = False
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
    id: int | None = None


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
    is_anchored: bool = False


class ImageCacheStatsResponse(BaseModel):
    """Response for image cache stats."""

    is_enabled: bool = False
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

    is_valid: bool = False
    is_face_detected: bool = False
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
    is_valid: bool = False
    is_face_detected: bool = False
    face_count: int = 0
    face_size_ratio: float = 0.0
    is_resolution_ok: bool = True
    width: int = 0
    height: int = 0
    warnings: list[str] = []


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
    """Response for POST /scene/validate-image."""

    mode: str = "hybrid"
    match_rate: float = 0.0
    adjusted_match_rate: float = 0.0  # deprecated: same as wd14_match_rate
    wd14_match_rate: float = 0.0  # Phase 33: WD14-only match rate
    matched: list[str] = []
    missing: list[str] = []
    extra: list[str] = []
    skipped: list[str] = []
    partial_matched: list[str] = []
    tags: list[str] = []
    critical_failure: CriticalFailureInfo | None = None
    identity_score: float | None = None
    # Phase 33: Gemini deferred evaluation metadata
    gemini_tokens: list[str] = []  # Tags pending Gemini evaluation


class BatchValidateRequest(BaseModel):
    """Batch validate multiple scenes (E-2: Gemini 호출 병합)."""

    scenes: list[SceneValidateRequest]


class BatchValidateResult(BaseModel):
    """Single scene validation result within a batch."""

    index: int
    status: Literal["success", "failed"]
    data: SceneValidationResponse | None = None
    error: str | None = None


class BatchValidateResponse(BaseModel):
    """Response for POST /scene/validate-batch."""

    results: list[BatchValidateResult]
    total: int
    succeeded: int
    failed: int
    gemini_pending: int = 0  # Scenes with pending Gemini evaluation


class VideoCreateResponse(BaseModel):
    """Response for POST /video/create (sync)."""

    video_url: str
    media_asset_id: int | None = None
    render_history_id: int | None = None


class VideoDeleteResponse(BaseModel):
    """Response for POST /video/delete."""

    ok: bool
    is_deleted: bool = False
    asset_id: int | None = None
    is_legacy: bool | None = None
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


# ============================================================
# Topic Analyze Schemas
# ============================================================


class ChatMessageItem(BaseModel):
    """대화 이력 메시지."""

    role: Literal["user", "assistant"]
    text: str = Field(max_length=2000)


class TopicAnalyzeRequest(BaseModel):
    """POST /scripts/analyze-topic 요청."""

    topic: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    group_id: int | None = None
    storyboard_id: int | None = None  # Draft storyboard ID (트레이싱/로깅용)
    messages: list[ChatMessageItem] | None = Field(default=None, max_length=20)


class AvailableOptions(BaseModel):
    """인라인 편집용 옵션 목록 (duration, language만 유의미. 구성/캐릭터는 Director SSOT)."""

    durations: list[int]
    languages: list[dict]  # [{value, label}]
    structures: list[dict] | None = None  # Director SSOT → 미사용
    characters: list[dict] | None = None  # Director SSOT → 미사용


class TopicAnalyzeResponse(BaseModel):
    """POST /scripts/analyze-topic 응답."""

    status: Literal["recommend", "clarify"] = "recommend"
    resolved_topic: str = ""  # 대화에서 추론한 최종 토픽 (Frontend topicRef 갱신용)
    questions: list[str] | None = None
    reasoning: str = ""
    # status=recommend 일 때 사용
    duration: int = 30
    language: str = DEFAULT_LANGUAGE
    structure: str = DEFAULT_STRUCTURE
    character_a_id: int | None = None  # Speaker A 캐릭터 ID
    character_a_name: str | None = None  # Speaker A 캐릭터 이름
    character_b_id: int | None = None  # Speaker B 캐릭터 ID
    character_b_name: str | None = None  # Speaker B 캐릭터 이름
    available_options: AvailableOptions | None = None


class GroupDefaultsResponse(BaseModel):
    """GET /groups/{group_id}/defaults 응답."""

    duration: int
    structure: str
    language: str
    character_a_id: int | None = None  # Speaker A 캐릭터 ID
    character_a_name: str | None = None  # Speaker A 캐릭터 이름
    character_b_id: int | None = None  # Speaker B 캐릭터 ID
    character_b_name: str | None = None  # Speaker B 캐릭터 이름
    has_history: bool
    available_options: AvailableOptions | None = None


# ============================================================
# Common Response Schemas (response_model enforcement)
# ============================================================


class OkDeletedResponse(BaseModel):
    """Common response for soft/hard delete operations."""

    ok: bool
    deleted: str


class OkRestoredResponse(BaseModel):
    """Common response for restore operations."""

    ok: bool
    restored: str


class SuccessMessageResponse(BaseModel):
    """Common response for operations that return success + message."""

    success: bool
    message: str


# ============================================================
# ControlNet Response Schemas
# ============================================================


class ControlNetStatusResponse(BaseModel):
    """Response for GET /controlnet/status."""

    is_available: bool
    models: list[str]
    pose_references: list[str]


class PoseInfoItem(BaseModel):
    """Single pose info."""

    name: str
    filename: str
    is_available: bool


class PoseListResponse(BaseModel):
    """Response for GET /controlnet/poses."""

    poses: list[PoseInfoItem]


class PoseReferenceResponse(BaseModel):
    """Response for GET /controlnet/pose/{name}."""

    pose_name: str
    image_b64: str


class SuggestPoseResponse(BaseModel):
    """Response for POST /controlnet/suggest-pose."""

    suggested_pose: str | None
    is_available: bool
    image_b64: str | None


class IPAdapterStatusResponse(BaseModel):
    """Response for GET /controlnet/ip-adapter/status."""

    is_available: bool
    models: list[str]
    supported_models: list[str]


class ReferencePreset(BaseModel):
    """IP-Adapter reference preset info."""

    weight: float
    model: str
    description: str | None = None


class ReferenceItem(BaseModel):
    """Single IP-Adapter reference."""

    character_key: str
    character_id: int | None = None
    filename: str | None = None
    image_b64: str | None = None
    image_url: str | None = None  # Response-only: derived from character.reference_image_url
    preset: ReferencePreset | None = None


class ReferenceListResponse(BaseModel):
    """Response for GET /controlnet/ip-adapter/references."""

    references: list[ReferenceItem]


class DeletedKeyResponse(BaseModel):
    """Response for DELETE /controlnet/ip-adapter/reference/{key}."""

    deleted: str


# ============================================================
# SD WebUI Proxy Response Schemas
# ============================================================


class SDWebUIModelsResponse(BaseModel):
    """Response for GET /sd/models."""

    models: list


class SDWebUIOptionsResponse(BaseModel):
    """Response for GET /sd/options."""

    options: dict
    model: str


class SDWebUIOptionsUpdateResponse(BaseModel):
    """Response for POST /sd/options."""

    ok: bool
    model: str


class SDWebUILorasResponse(BaseModel):
    """Response for GET /sd/loras."""

    loras: list


# ============================================================
# Characters Extra Response Schemas
# ============================================================


class TrashedItem(BaseModel):
    """Item in trashed list (characters, storyboards, etc.)."""

    id: int
    name: str
    deleted_at: str | None = None


class BatchRegenerateResultItem(BaseModel):
    """Single item in batch-regenerate results."""

    id: int
    name: str
    status: str
    error: str | None = None


class BatchRegenerateResponse(BaseModel):
    """Response for POST /characters/batch-regenerate-references."""

    ok: bool
    results: list[BatchRegenerateResultItem]


# ============================================================
# Admin Response Schemas
# ============================================================


class CacheRefreshResponse(BaseModel):
    """Response for POST /refresh-caches (200 or 207)."""

    success: bool
    message: str
    refreshed: list[str] = []
    failures: list[dict] = []


class ReplacementTagInfo(BaseModel):
    """Replacement tag summary."""

    id: int
    name: str
    category: str | None = None


class DeprecatedTagItem(BaseModel):
    """Single deprecated tag."""

    id: int
    name: str
    category: str | None = None
    deprecated_reason: str | None = None
    replacement: ReplacementTagInfo | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DeprecatedTagsResponse(BaseModel):
    """Response for GET /tags/deprecated."""

    total: int
    tags: list[DeprecatedTagItem]


class DeprecatedTagInfo(BaseModel):
    """Tag info after deprecation."""

    id: int
    name: str
    is_active: bool
    deprecated_reason: str | None = None
    replacement_tag_id: int | None = None


class DeprecateTagResponse(BaseModel):
    """Response for PUT /tags/{id}/deprecate."""

    success: bool
    tag: DeprecatedTagInfo


class ActivatedTagInfo(BaseModel):
    """Tag info after activation."""

    id: int
    name: str
    is_active: bool


class ActivateTagResponse(BaseModel):
    """Response for PUT /tags/{id}/activate."""

    success: bool
    tag: ActivatedTagInfo


class OrphanInfo(BaseModel):
    """Single orphan asset info."""

    id: int
    storage_key: str
    owner_type: str | None = None
    owner_id: int | None = None
    reason: str


class MediaOrphanResponse(BaseModel):
    """Response for GET /media-assets/orphans."""

    success: bool
    total: int | None = None
    null_owner: list[OrphanInfo] | None = None
    broken_fk: list[OrphanInfo] | None = None
    expired_temp: list[OrphanInfo] | None = None
    error: str | None = None


class MediaCleanupResponse(BaseModel):
    """Response for POST /media-assets/cleanup."""

    success: bool
    orphans: dict | None = None
    expired_temp: dict | None = None
    total_deleted: int | None = None
    error: str | None = None


class MediaStatsResponse(BaseModel):
    """Response for GET /media-assets/stats."""

    success: bool
    total_assets: int | None = None
    temp_assets: int | None = None
    null_owner_assets: int | None = None
    orphan_count: int | None = None
    by_owner_type: dict[str, int] | None = None
    error: str | None = None


class CleanupResultDetail(BaseModel):
    """Cleanup operation result detail."""

    deleted: int = 0
    storage_errors: list[str] = []
    is_dry_run: bool = True


class DanglingCandidateDetail(BaseModel):
    """Dangling candidates cleanup result."""

    scenes_affected: int = 0
    candidates_removed: int = 0
    is_dry_run: bool = True


class OrphanAssetCleanupResponse(BaseModel):
    """Response for POST /admin/cleanup-orphan-assets."""

    success: bool
    orphans: CleanupResultDetail | None = None
    expired_temp: CleanupResultDetail | None = None
    dangling_candidates: DanglingCandidateDetail | None = None
    total_deleted: int | None = None
    error: str | None = None


class DirectoryStatsItem(BaseModel):
    """Storage stats for a single directory."""

    count: int
    size_mb: float


class StorageStatsResponse(BaseModel):
    """Response for GET /storage/stats."""

    total_size_mb: float
    total_count: int
    directories: dict[str, DirectoryStatsItem]


class CleanupCategoryDetail(BaseModel):
    """Cleanup result for a single category."""

    deleted: int
    freed_mb: float
    files: list[str] = []


class StorageCleanupResponse(BaseModel):
    """Response for POST /storage/cleanup and /storage/cleanup/preview."""

    deleted_count: int
    freed_mb: float
    is_dry_run: bool
    details: dict[str, CleanupCategoryDetail]


# ============================================================
# ============================================================
# Tags Extra Response Schemas
# ============================================================


class TagGroupItem(BaseModel):
    """Single tag group with count."""

    category: str | None = None
    group_name: str | None = None
    count: int
    description: str | None = None


class TagGroupsResponse(BaseModel):
    """Response for GET /tags/groups."""

    groups: list[TagGroupItem]


class ApproveClassificationResponse(BaseModel):
    """Response for POST /tags/approve-classification."""

    ok: bool
    tag: str
    group_name: str
    category: str | None = None


class BulkApproveResponse(BaseModel):
    """Response for POST /tags/bulk-approve-classifications."""

    ok: bool
    approved_count: int
    approved: list[str]
    failed: list[dict]


# ============================================================
# Assets Response Schemas
# ============================================================


class AudioItem(BaseModel):
    """Single audio file."""

    name: str
    url: str


class AudioListResponse(BaseModel):
    """Response for GET /audio/list."""

    audios: list[AudioItem]


class FontItem(BaseModel):
    """Single font file."""

    name: str


class FontListResponse(BaseModel):
    """Response for GET /fonts/list."""

    fonts: list[FontItem]


class OverlayItem(BaseModel):
    """Single overlay frame."""

    id: str
    name: str
    url: str


class OverlayListResponse(BaseModel):
    """Response for GET /overlay/list."""

    overlays: list[OverlayItem]


# ============================================================
# Prompt History Extra Response Schemas
# ============================================================


# ============================================================
# Delete Status Response (groups, projects)
# ============================================================


class DeleteStatusResponse(BaseModel):
    """Response for DELETE operations returning status + id."""

    status: str
    id: int


# ============================================================
# Activity Logs Response Schemas
# ============================================================


class ActivityLogCreatedResponse(BaseModel):
    """Response for POST /activity-logs."""

    id: int
    storyboard_id: int | None = None
    scene_id: int | None = None
    character_id: int | None = None
    status: str | None = None
    match_rate: float | None = None


class ActivityLogItem(BaseModel):
    """Single activity log entry."""

    id: int
    storyboard_id: int | None = None
    scene_id: int | None = None
    character_id: int | None = None
    prompt: str | None = None
    tags: list[str] | None = None
    sd_params: dict | None = None
    match_rate: float | None = None
    seed: int | None = None
    status: str | None = None
    image_url: str | None = None
    created_at: str | None = None


class StoryboardLogsResponse(BaseModel):
    """Response for GET /activity-logs/storyboard/{id}."""

    logs: list[ActivityLogItem]
    total: int


class UpdateStatusLogResponse(BaseModel):
    """Response for PATCH /activity-logs/{id}/status."""

    id: int
    status: str
    match_rate: float | None = None


class DeleteLogResponse(BaseModel):
    """Response for DELETE /activity-logs/{id}."""

    message: str


class PatternSummary(BaseModel):
    """Summary section in analyze/patterns."""

    total_logs: int
    success_count: int
    fail_count: int
    avg_match_rate: float


class TagStatItem(BaseModel):
    """Single tag stat in analyze/patterns."""

    tag: str
    total: int
    success: int
    fail: int
    success_rate: float
    avg_match_rate: float


class ConflictCandidateItem(BaseModel):
    """Single conflict candidate."""

    tag1: str
    tag2: str
    co_occurrence: int
    fail_count: int
    fail_rate: float
    avg_match_rate: float
    reason: str | None = None


class AnalyzePatternsResponse(BaseModel):
    """Response for GET /activity-logs/analyze/patterns."""

    summary: PatternSummary
    tag_stats: list[TagStatItem]
    conflict_candidates: list[ConflictCandidateItem]


class SuggestConflictRulesResponse(BaseModel):
    """Response for GET /activity-logs/suggest-conflict-rules."""

    suggested_rules: list[ConflictCandidateItem]
    existing_rules_count: int
    new_rules_count: int


class TagSuccessItem(BaseModel):
    """Single tag success item."""

    tag: str
    success_rate: float
    occurrences: int
    avg_match_rate: float
    group: str | None = None


class SuggestedCombination(BaseModel):
    """Single suggested tag combination."""

    tags: list[str]
    categories: list[str]
    avg_success_rate: float
    is_conflict_free: bool


class SuccessCombinationSummary(BaseModel):
    """Summary for success-combinations."""

    total_success: int
    analyzed_tags: int
    categories_found: int


class SuccessCombinationsResponse(BaseModel):
    """Response for GET /activity-logs/success-combinations."""

    summary: SuccessCombinationSummary
    combinations_by_category: dict[str, list[TagSuccessItem]]
    suggested_combinations: list[SuggestedCombination]


class ApplyRuleDetail(BaseModel):
    """Single rule apply result."""

    tag1: str
    tag2: str
    status: str
    reason: str | None = None


class ApplyConflictRulesResponse(BaseModel):
    """Response for POST /activity-logs/apply-conflict-rules."""

    applied_count: int
    skipped_count: int
    details: list[ApplyRuleDetail]


# ============================================================
# Lab Extra Response Schemas
# ============================================================


class OkResponse(BaseModel):
    """Generic ok response."""

    ok: bool


class SyncedCountResponse(BaseModel):
    """Response for sync operations."""

    synced: int


# ============================================================
# Script Edit Schemas (P1 — Scene Edit via Gemini)
# ============================================================


class ScriptEditSceneInput(BaseModel):
    """씬 편집 입력 — 현재 씬 상태."""

    scene_index: int
    script: str = ""
    speaker: str = DEFAULT_SPEAKER
    duration: float = 3.0
    image_prompt: str = ""
    image_prompt_ko: str = ""


class ScriptEditContext(BaseModel):
    """편집 컨텍스트 — 스토리 전체 정보."""

    topic: str = ""
    language: str = DEFAULT_LANGUAGE
    structure: str = DEFAULT_STRUCTURE


class ScriptEditRequest(BaseModel):
    """POST /scripts/edit-scenes 요청."""

    instruction: str = Field(min_length=1, max_length=2000)
    scenes: list[ScriptEditSceneInput] = Field(min_length=1, max_length=30)
    context: ScriptEditContext = Field(default_factory=ScriptEditContext)


class ScriptEditedScene(BaseModel):
    """수정된 씬 — 변경된 필드만 non-null."""

    scene_index: int
    script: str | None = None
    speaker: str | None = None
    duration: float | None = None
    image_prompt: str | None = None
    image_prompt_ko: str | None = None


class ScriptEditResponse(BaseModel):
    """POST /scripts/edit-scenes 응답."""

    edited_scenes: list[ScriptEditedScene]
    reasoning: str = ""
    unchanged_count: int = 0


# ============================================================
# Preview Schemas (Phase 29 — Video Pre-validation)
# ============================================================


class SceneTTSPreviewRequest(_SceneEmotionCoerce, BaseModel):
    """POST /preview/tts — 개별 씬 TTS 프리뷰 요청."""

    script: str = Field(max_length=2000)
    speaker: str = DEFAULT_SPEAKER
    storyboard_id: int | None = None
    scene_db_id: int | None = None  # 제공 시 Scene.tts_asset_id DB 즉시 반영
    voice_preset_id: int | None = None
    voice_design_prompt: str | None = None
    scene_emotion: str | None = None
    image_prompt_ko: str | None = None  # Gemini voice_design 컨텍스트용
    language: str = "korean"
    force_regenerate: bool = False


class SceneTTSPreviewResponse(BaseModel):
    """POST /preview/tts — 개별 씬 TTS 프리뷰 응답."""

    audio_url: str
    duration: float
    cache_key: str
    cached: bool
    voice_seed: int | None = None
    voice_design: str | None = None
    temp_asset_id: int


class BatchTTSPreviewRequest(BaseModel):
    """POST /preview/tts-batch — 일괄 TTS 프리뷰 요청."""

    scenes: list[SceneTTSPreviewRequest] = Field(max_length=30)
    storyboard_id: int | None = None
    voice_preset_id: int | None = None


class BatchTTSPreviewItem(BaseModel):
    """배치 TTS 프리뷰 개별 결과."""

    scene_index: int
    status: Literal["success", "cached", "failed"]
    audio_url: str | None = None
    duration: float | None = None
    cache_key: str
    error: str | None = None
    temp_asset_id: int | None = None


class BatchTTSPreviewResponse(BaseModel):
    """POST /preview/tts-batch — 일괄 TTS 프리뷰 응답."""

    items: list[BatchTTSPreviewItem]
    total_duration: float
    cached_count: int
    generated_count: int
    failed_count: int


class TtsPrebuildSceneItem(_SceneEmotionCoerce, BaseModel):
    """TTS 프리빌드 요청의 씬 단위 항목."""

    scene_db_id: int
    script: str
    speaker: str = DEFAULT_SPEAKER
    voice_design_prompt: str | None = None
    tts_asset_id: int | None = None  # 이미 있으면 스킵
    scene_emotion: str | None = None  # 캐시 키 일치 + Gemini voice design용
    image_prompt_ko: str | None = None  # Gemini voice design 컨텍스트용
    language: str | None = None  # TTS 언어 (None → TTS_DEFAULT_LANGUAGE fallback)


class TtsPrebuildRequest(BaseModel):
    """POST /scene/tts-prebuild — TTS 사전 생성 요청."""

    storyboard_id: int
    scenes: list[TtsPrebuildSceneItem] = Field(max_length=50)
    tts_engine: str = DEFAULT_TTS_ENGINE


class TtsPrebuildResult(BaseModel):
    """TTS 프리빌드 씬별 결과."""

    scene_db_id: int
    tts_asset_id: int | None
    status: Literal["prebuilt", "skipped", "failed"]
    duration: float = 0.0
    error: str | None = None


class TtsPrebuildResponse(BaseModel):
    """POST /scene/tts-prebuild — TTS 사전 생성 응답."""

    results: list[TtsPrebuildResult]
    prebuilt: int
    skipped: int
    failed: int


class BgmPrebuildRequest(BaseModel):
    """POST /storyboards/{id}/stage/bgm-prebuild — BGM 사전 생성 요청."""

    bgm_prompt: str | None = None
    total_duration: float | None = None  # 씬 duration 합계 (BGM 길이 결정)


class BgmPrebuildResponse(BaseModel):
    """POST /storyboards/{id}/stage/bgm-prebuild — BGM 사전 생성 응답."""

    status: Literal["prebuilt", "skipped", "no_prompt", "failed"]
    bgm_audio_asset_id: int | None = None
    error: str | None = None


class SceneFramePreviewRequest(BaseModel):
    """POST /preview/frame — 개별 씬 프레임 합성 요청."""

    image_url: str = Field(pattern=r"^(https?://|/outputs/).+")
    script: str = ""
    layout_style: Literal["full", "post"] = "post"
    include_scene_text: bool = True
    scene_text_font: str | None = None
    channel_name: str | None = None
    caption: str | None = None
    width: int = 1080
    height: int = 1920


class FrameLayoutInfo(BaseModel):
    """프레임 레이아웃 분석 정보."""

    font_size: int | None = None
    is_face_detected: bool = False
    text_brightness: float | None = None


class SceneFramePreviewResponse(BaseModel):
    """POST /preview/frame — 프레임 합성 응답."""

    preview_url: str
    temp_asset_id: int
    layout_info: FrameLayoutInfo


class TimelineSceneInput(BaseModel):
    """타임라인 씬 입력."""

    script: str = ""
    duration: float = 3.0
    tts_duration: float | None = None


class TimelineRequest(BaseModel):
    """POST /preview/timeline — 타임라인 데이터 요청."""

    scenes: list[TimelineSceneInput] = Field(max_length=30)
    speed_multiplier: float = 1.0
    transition_type: str = "fade"


class TimelineSceneOutput(BaseModel):
    """타임라인 씬 출력."""

    scene_index: int
    effective_duration: float
    tts_duration: float | None = None
    has_tts: bool = False
    start_time: float = 0.0
    end_time: float = 0.0


class TimelineResponse(BaseModel):
    """POST /preview/timeline — 타임라인 응답."""

    scenes: list[TimelineSceneOutput]
    total_duration: float


class PreValidateIssue(BaseModel):
    """사전 검증 이슈 항목."""

    level: Literal["error", "warning", "info"]
    scene_index: int | None = None
    category: str
    message: str


class PreValidateRequest(BaseModel):
    """POST /preview/validate — 사전 검증 요청."""

    storyboard_id: int


class PreValidateResponse(BaseModel):
    """POST /preview/validate — 사전 검증 응답."""

    is_ready: bool
    issues: list[PreValidateIssue]
    total_duration: float | None = None
    cached_tts_count: int = 0
    total_scenes: int = 0


# ============================================================
# Story Card Schemas
# ============================================================


class StoryCardCreate(BaseModel):
    """POST /groups/{group_id}/story-cards — 소재 카드 생성."""

    cluster: str | None = None
    title: str = Field(max_length=300)
    situation: str | None = None
    hook_angle: str | None = None
    key_moments: list[str] | None = None
    emotional_arc: dict | None = None
    empathy_details: list[str] | None = None
    characters_hint: dict | None = None


class StoryCardUpdate(BaseModel):
    """PATCH /story-cards/{id} — 소재 카드 수정."""

    cluster: str | None = None
    title: str | None = Field(default=None, max_length=300)
    status: str | None = Field(default=None, pattern=r"^(unused|used|retired)$")
    situation: str | None = None
    hook_angle: str | None = None
    key_moments: list[str] | None = None
    emotional_arc: dict | None = None
    empathy_details: list[str] | None = None
    characters_hint: dict | None = None


class StoryCardResponse(BaseModel):
    """소재 카드 응답."""

    id: int
    group_id: int
    cluster: str | None = None
    title: str
    status: str
    situation: str | None = None
    hook_angle: str | None = None
    key_moments: list[str] | None = None
    emotional_arc: dict | None = None
    empathy_details: list[str] | None = None
    characters_hint: dict | None = None
    hook_score: float | None = None
    used_in_storyboard_id: int | None = None
    used_at: datetime | None = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class StoryCardGenerateRequest(BaseModel):
    """POST /groups/{group_id}/story-cards/generate — Gemini 소재 대량 생성."""

    cluster: str = Field(max_length=100)
    count: int = Field(default=5, ge=1, le=20)


class StoryCardListResponse(BaseModel):
    """소재 카드 목록 응답."""

    items: list[StoryCardResponse]
    total: int
