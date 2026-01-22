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


class SDModelRequest(BaseModel):
    sd_model_checkpoint: str


class KeywordApproveRequest(BaseModel):
    tag: str
    category: str
