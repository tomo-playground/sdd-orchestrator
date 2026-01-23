"""API Routers for Shorts Producer Backend."""

from .assets import router as assets_router
from .keywords import router as keywords_router

__all__ = ["assets_router", "keywords_router"]
