"""API Routers for Shorts Producer Backend."""

from .assets import router as assets_router
from .avatar import router as avatar_router
from .characters import router as characters_router
from .cleanup import router as cleanup_router
from .controlnet import router as controlnet_router
from .keywords import router as keywords_router
from .loras import router as loras_router
from .presets import router as presets_router
from .prompt import router as prompt_router
from .scene import router as scene_router
from .sd import router as sd_router
from .storyboard import router as storyboard_router
from .sd_models import router as sd_models_router
from .style_profiles import router as style_profiles_router
from .tags import router as tags_router
from .video import router as video_router

__all__ = [
    "assets_router",
    "avatar_router",
    "characters_router",
    "cleanup_router",
    "controlnet_router",
    "keywords_router",
    "loras_router",
    "presets_router",
    "prompt_router",
    "scene_router",
    "sd_models_router",
    "sd_router",
    "storyboard_router",
    "style_profiles_router",
    "tags_router",
    "video_router",
]
