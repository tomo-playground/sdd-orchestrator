"""API Routers for Shorts Producer Backend."""

from .activity_logs import router as activity_logs_router
from .admin import router as admin_router
from .analytics import router as analytics_router
from .assets import router as assets_router
from .avatar import router as avatar_router
from .backgrounds import router as backgrounds_router
from .characters import router as characters_router
from .cleanup import router as cleanup_router
from .controlnet import router as controlnet_router
from .creative import router as creative_router
from .creative_presets import router as creative_presets_router
from .groups import router as groups_router
from .keywords import router as keywords_router
from .lab import router as lab_router
from .loras import router as loras_router
from .memory import router as memory_router
from .music_presets import router as music_presets_router
from .presets import router as presets_router
from .projects import router as projects_router
from .prompt import router as prompt_router
from .prompt_histories import router as prompt_histories_router
from .quality import router as quality_router
from .render_presets import router as render_presets_router
from .scene import router as scene_router
from .scripts import router as scripts_router
from .sd import router as sd_router
from .sd_models import router as sd_models_router
from .settings import router as settings_router
from .storyboard import router as storyboard_router
from .style_profiles import router as style_profiles_router
from .tags import router as tags_router
from .video import router as video_router
from .voice_presets import router as voice_presets_router
from .youtube import router as youtube_router

__all__ = [
    "admin_router",
    "analytics_router",
    "assets_router",
    "avatar_router",
    "backgrounds_router",
    "characters_router",
    "cleanup_router",
    "controlnet_router",
    "creative_router",
    "creative_presets_router",
    "keywords_router",
    "lab_router",
    "loras_router",
    "memory_router",
    "presets_router",
    "prompt_router",
    "prompt_histories_router",
    "quality_router",
    "scene_router",
    "scripts_router",
    "sd_models_router",
    "sd_router",
    "settings_router",
    "storyboard_router",
    "style_profiles_router",
    "tags_router",
    "video_router",
    "activity_logs_router",
    "groups_router",
    "projects_router",
    "render_presets_router",
    "voice_presets_router",
    "music_presets_router",
    "youtube_router",
]
