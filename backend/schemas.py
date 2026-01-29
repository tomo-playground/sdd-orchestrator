from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Type alias for prompt mode
PromptMode = Literal["auto", "standard", "lora"]


class CharacterLoRA(BaseModel):
    lora_id: int
    weight: float = 1.0
    name: str | None = None
    trigger_words: list[str] | None = None
    lora_type: str | None = None

class StoryboardBase(BaseModel):
    title: str
    description: str | None = None
    default_character_id: int | None = None
    default_style_profile_id: int | None = None

class StoryboardSave(StoryboardBase):
    scenes: list[StoryboardScene]

class StoryboardResponse(StoryboardBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class StoryboardRequest(BaseModel):
    topic: str
    duration: int = 10
    style: str = "Anime"
    language: str = "Korean"
    structure: str = "Monologue"
    actor_a_gender: str = "female"


class StoryboardScene(BaseModel):
    scene_id: int
    script: str
    speaker: str = "Narrator"
    duration: float = 3
    image_prompt: str = ""
    image_prompt_ko: str = ""
    image_url: str | None = None
    description: str | None = None
    width: int = 512
    height: int = 768
    
    # V3 Data Persistence
    tags: list[SceneTagSave] | None = None
    character_actions: list[SceneActionSave] | None = None

    model_config = ConfigDict(extra="allow")

class SceneTagSave(BaseModel):
    tag_id: int
    weight: float = 1.0

class SceneActionSave(BaseModel):
    character_id: int
    tag_id: int
    weight: float = 1.0


class VideoScene(BaseModel):
    image_url: str
    script: str = ""
    speaker: str = "Narrator"
    duration: float = 3

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


class AvatarRegenerateRequest(BaseModel):
    avatar_key: str


class AvatarResolveRequest(BaseModel):
    avatar_key: str


class VideoRequest(BaseModel):
    scenes: list[VideoScene]
    project_name: str = "my_shorts"
    bgm_file: str | None = None
    width: int = 1080
    height: int = 1920
    layout_style: str = "post"
    ken_burns_preset: str = "none"  # Ken Burns preset (10 options)
    ken_burns_intensity: float = 1.0  # Effect intensity (0.5~2.0)
    transition_type: str = "fade"  # Scene transition effect
    narrator_voice: str = "ko-KR-SunHiNeural"
    speed_multiplier: float = 1.0
    include_subtitles: bool = True
    subtitle_font: str | None = None
    overlay_settings: OverlaySettings | None = None
    post_card_settings: PostCardSettings | None = None
    audio_ducking: bool = True
    bgm_volume: float = 0.25
    ducking_threshold: float = 0.01


class VideoDeleteRequest(BaseModel):
    filename: str


class SceneGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    steps: int = 24
    cfg_scale: float = 7.0
    sampler_name: str = "DPM++ 2M Karras"
    seed: int = -1
    width: int = 512
    height: int = 768
    clip_skip: int = 2
    enable_hr: bool = False
    hr_scale: float = 1.5
    hr_upscaler: str = "Latent"
    hr_second_pass_steps: int = 10
    denoising_strength: float = 0.25
    # V3 Character Integration
    character_id: int | None = None
    # ControlNet options
    use_controlnet: bool = False
    controlnet_pose: str | None = None  # Specific pose name or None for auto-detect
    controlnet_weight: float = 1.0
    # IP-Adapter options
    use_ip_adapter: bool = False
    ip_adapter_reference: str | None = None  # character_key for saved reference
    ip_adapter_weight: float = 0.7
    # Analytics tracking (optional, all fields auto-generated if not provided)
    session_id: str | None = None  # Optional: Frontend session ID (uses date if not provided)
    topic: str | None = None  # Optional: Content topic for reference
    scene_index: int | None = None  # Optional: Scene number  # Scene number within session  # Scene number within project  # Scene number within project


class SceneValidateRequest(BaseModel):
    image_b64: str
    prompt: str = ""
    # Analytics tracking (optional, auto-generated if not provided)
    session_id: str | None = None  # Optional: Frontend session ID
    topic: str | None = None  # Optional: Content topic for reference
    scene_index: int | None = None  # Optional: Scene number


class ImageStoreRequest(BaseModel):
    image_b64: str


class PromptRewriteRequest(BaseModel):
    base_prompt: str
    scene_prompt: str
    style: str = "Anime"
    mode: str = "compose"


class PromptSplitRequest(BaseModel):
    example_prompt: str
    style: str = "Anime"


class PromptValidateRequest(BaseModel):
    """Request for validating prompt before image generation."""

    positive: str
    negative: str = ""


class PromptComposeLoRA(BaseModel):
    """LoRA info for prompt composition."""

    name: str
    weight: float = 0.5
    trigger_words: list[str] | None = None
    lora_type: str | None = None  # character, style, concept
    optimal_weight: float | None = None
    calibration_score: int | None = None


class PromptComposeRequest(BaseModel):
    """Request for composing a prompt with Mode A/B logic."""

    tokens: list[str]  # Raw prompt tokens
    mode: PromptMode = "auto"  # auto, standard, lora
    loras: list[PromptComposeLoRA] | None = None
    use_break: bool = True  # Insert BREAK token in Mode B


class PromptComposeResponse(BaseModel):
    """Response from prompt composition."""

    prompt: str  # Final composed prompt string
    tokens: list[str]  # Ordered token list
    effective_mode: str  # standard or lora
    scene_complexity: str  # simple, moderate, complex
    lora_weights: dict[str, float] | None = None  # Calculated weights per LoRA
    meta: dict | None = None  # Additional metadata


class SDModelRequest(BaseModel):
    sd_model_checkpoint: str


class KeywordApproveRequest(BaseModel):
    tag: str
    category: str


class BatchApproveRequest(BaseModel):
    tags: list[str] | None = None
    min_confidence: float = 0.7


# ============================================================
# Phase 6: Tag/LoRA/Character CRUD Schemas
# ============================================================


class TagBase(BaseModel):
    name: str
    ko_name: str | None = None
    category: str | None = None
    group_name: str | None = None
    priority: int = 100
    default_layer: int = 0
    usage_scope: str = "ANY"
    wd14_count: int = 0
    wd14_category: int = 0
    classification_source: str | None = None
    classification_confidence: float | None = None

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: str | None = None
    ko_name: str | None = None
    default_layer: int | None = None
    usage_scope: str | None = None

class TagResponse(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LoRABase(BaseModel):
    name: str
    display_name: str | None = None
    lora_type: str | None = None  # character, style, pose
    trigger_words: list[str] | None = None
    default_weight: float = 0.7
    optimal_weight: float | None = None
    calibration_score: int | None = None
    weight_min: float = 0.1
    weight_max: float = 1.0
    gender_locked: str | None = None
    civitai_id: int | None = None
    civitai_url: str | None = None
    preview_image_url: str | None = None


class LoRACreate(LoRABase):
    pass


class LoRAUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    lora_type: str | None = None
    trigger_words: list[str] | None = None
    default_weight: float | None = None
    optimal_weight: float | None = None
    calibration_score: int | None = None
    weight_min: float | None = None
    weight_max: float | None = None
    preview_image_url: str | None = None


class LoRAResponse(LoRABase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CharacterTagLink(BaseModel):
    tag_id: int
    name: str | None = None # Tag name for display
    layer: int | None = None # Tag default_layer
    weight: float = 1.0
    is_permanent: bool = True

class CharacterBase(BaseModel):
    name: str
    description: str | None = None
    gender: str | None = None
    loras: list[CharacterLoRA] | None = None
    recommended_negative: list[str] | None = None
    custom_base_prompt: str | None = None
    custom_negative_prompt: str | None = None
    reference_base_prompt: str | None = None
    reference_negative_prompt: str | None = None
    preview_image_url: str | None = None
    prompt_mode: PromptMode = "auto"
    ip_adapter_weight: float | None = None
    ip_adapter_model: str | None = None

class CharacterCreate(CharacterBase):
    tags: list[CharacterTagLink] | None = None
    # Legacy support (will be migrated to tags in router)
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None

class CharacterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    gender: str | None = None
    loras: list[CharacterLoRA] | None = None
    recommended_negative: list[str] | None = None
    custom_base_prompt: str | None = None
    custom_negative_prompt: str | None = None
    reference_base_prompt: str | None = None
    reference_negative_prompt: str | None = None
    preview_image_url: str | None = None
    prompt_mode: PromptMode | None = None
    ip_adapter_weight: float | None = None
    ip_adapter_model: str | None = None
    tags: list[CharacterTagLink] | None = None
    # Legacy support (will be migrated to tags in router)
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None

class CharacterResponse(CharacterBase):
    id: int
    tags: list[CharacterTagLink] = []

    model_config = ConfigDict(from_attributes=True)


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
    preview_image_url: str | None = None
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
    preview_image_url: str | None = None
    is_active: bool | None = None


class SDModelResponse(SDModelBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Embedding Schemas
# ============================================================


class EmbeddingBase(BaseModel):
    name: str
    display_name: str | None = None
    embedding_type: str = "negative"
    trigger_word: str | None = None
    description: str | None = None
    is_active: bool = True


class EmbeddingCreate(EmbeddingBase):
    pass


class EmbeddingUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    embedding_type: str | None = None
    trigger_word: str | None = None
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
    name: str
    display_name: str | None = None
    description: str | None = None
    sd_model_id: int | None = None
    loras: list[LoRAWeight] | None = None
    negative_embeddings: list[int] | None = None
    positive_embeddings: list[int] | None = None
    default_positive: str | None = None
    default_negative: str | None = None
    is_default: bool = False
    is_active: bool = True


class StyleProfileCreate(StyleProfileBase):
    pass


class StyleProfileUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    sd_model_id: int | None = None
    loras: list[LoRAWeight] | None = None
    negative_embeddings: list[int] | None = None
    positive_embeddings: list[int] | None = None
    default_positive: str | None = None
    default_negative: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class StyleProfileResponse(StyleProfileBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Activity Log Schemas (Unified Memory)
# ============================================================

class ActivityLogBase(BaseModel):
    project_name: str | None = None
    scene_id: int | None = None
    character_id: int | None = None
    prompt: str
    negative_prompt: str | None = None
    sd_params: dict | None = None
    seed: int | None = None
    image_url: str | None = None
    match_rate: float | None = None
    tags_used: list[str] | None = None
    is_favorite: bool = False
    name: str | None = None

class ActivityLogCreate(ActivityLogBase):
    pass

class ActivityLogUpdate(BaseModel):
    is_favorite: bool | None = None
    name: str | None = None

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

