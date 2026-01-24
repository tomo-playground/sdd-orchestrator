"""API Routers for Shorts Producer Backend."""

from .assets import router as assets_router
from .avatar import router as avatar_router
from .cleanup import router as cleanup_router
from .keywords import router as keywords_router
from .presets import router as presets_router
from .prompt import router as prompt_router
from .scene import router as scene_router
from .sd import router as sd_router
from .storyboard import router as storyboard_router
from .video import router as video_router

__all__ = [
    "assets_router",
    "avatar_router",
    "cleanup_router",
    "keywords_router",
    "presets_router",
    "prompt_router",
    "scene_router",
    "sd_router",
    "storyboard_router",
    "video_router",
]
