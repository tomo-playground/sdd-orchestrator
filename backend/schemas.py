from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(extra="allow")


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
    layout_style: str = "full"
    motion_style: str = "none"
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
    height: int = 512
    clip_skip: int = 2
    enable_hr: bool = False
    hr_scale: float = 1.5
    hr_upscaler: str = "Latent"
    hr_second_pass_steps: int = 10
    denoising_strength: float = 0.25
    # ControlNet options
    use_controlnet: bool = False
    controlnet_pose: str | None = None  # Specific pose name or None for auto-detect
    controlnet_weight: float = 1.0
    # IP-Adapter options
    use_ip_adapter: bool = False
    ip_adapter_reference: str | None = None  # character_key for saved reference
    ip_adapter_weight: float = 0.7


class SceneValidateRequest(BaseModel):
    image_b64: str
    prompt: str = ""
    mode: str = "wd14"


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


class SDModelRequest(BaseModel):
    sd_model_checkpoint: str


class KeywordApproveRequest(BaseModel):
    tag: str
    category: str


# ============================================================
# Phase 6: Tag/LoRA/Character CRUD Schemas
# ============================================================


class TagBase(BaseModel):
    name: str
    category: str  # character, scene, meta
    group_name: str | None = None
    priority: int = 5
    exclusive: bool = False


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    group_name: str | None = None
    priority: int | None = None
    exclusive: bool | None = None


class TagResponse(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LoRABase(BaseModel):
    name: str
    display_name: str | None = None
    gender_locked: str | None = None  # female, male, null(자유)
    civitai_id: int | None = None
    civitai_url: str | None = None
    trigger_words: list[str] | None = None
    default_weight: float = 0.7  # 0.7 optimal for scene expression
    weight_min: float = 0.5
    weight_max: float = 1.5
    base_models: list[str] | None = None
    character_defaults: dict | None = None
    recommended_negative: list[str] | None = None
    preview_image_url: str | None = None


class LoRACreate(LoRABase):
    pass


class LoRAUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    gender_locked: str | None = None
    civitai_id: int | None = None
    civitai_url: str | None = None
    trigger_words: list[str] | None = None
    default_weight: float | None = None
    weight_min: float | None = None
    weight_max: float | None = None
    base_models: list[str] | None = None
    character_defaults: dict | None = None
    recommended_negative: list[str] | None = None
    preview_image_url: str | None = None


class LoRAResponse(LoRABase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CharacterLoRA(BaseModel):
    lora_id: int
    weight: float = 1.0


class CharacterBase(BaseModel):
    name: str
    description: str | None = None
    gender: str | None = None  # female, male
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None
    loras: list[CharacterLoRA] | None = None
    recommended_negative: list[str] | None = None
    preview_image_url: str | None = None


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    gender: str | None = None
    identity_tags: list[int] | None = None
    clothing_tags: list[int] | None = None
    loras: list[CharacterLoRA] | None = None
    recommended_negative: list[str] | None = None
    preview_image_url: str | None = None


class CharacterResponse(CharacterBase):
    id: int

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
