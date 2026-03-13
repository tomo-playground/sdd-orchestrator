"""API Routers for Shorts Producer Backend.

Assembles all routers into two parent routers:
  - service_app_router (/api/v1)  — user-facing Service API
  - admin_app_router   (/api/admin) — back-office Admin API
"""

from fastapi import APIRouter

# ── Parent routers ──────────────────────────────────────────
service_app_router = APIRouter(prefix="/api/v1")
admin_app_router = APIRouter(prefix="/api/admin")

# ── Service-only routers (11) ──────────────────────────────
from .assets import router as assets_router
from .controlnet import service_router as controlnet_svc
from .groups import admin_router as group_adm
from .groups import router as groups_router
from .presets import router as presets_router
from .preview import service_router as preview_svc
from .projects import router as projects_router
from .scene import router as scene_router
from .scripts import router as scripts_router
from .stage import router as stage_router
from .storyboard import admin_router as storyboard_adm
from .storyboard import router as storyboard_router
from .video import router as video_router

for _r in [
    projects_router,
    groups_router,
    storyboard_router,
    scripts_router,
    scene_router,
    video_router,
    presets_router,
    assets_router,
    stage_router,
    controlnet_svc,
    preview_svc,
]:
    service_app_router.include_router(_r)

# ── Admin-only routers (7) ──────────────────────────────────
from .activity_logs import router as activity_logs_router
from .admin import router as admin_core_router
from .controlnet import router as controlnet_router
from .creative_presets import router as creative_presets_router
from .sd_models import router as sd_models_router
from .settings import router as settings_router

for _r in [
    admin_core_router,
    settings_router,
    sd_models_router,
    controlnet_router,
    creative_presets_router,
    activity_logs_router,
    storyboard_adm,
    group_adm,
]:
    admin_app_router.include_router(_r)

# ── Split routers (11 service + 10 admin) ─────────────────────
from .backgrounds import admin_router as bg_adm
from .backgrounds import service_router as bg_svc
from .loras import admin_router as lora_adm
from .loras import service_router as lora_svc
from .characters import admin_router as char_adm
from .characters import service_router as char_svc
from .music_presets import admin_router as music_adm
from .music_presets import service_router as music_svc
from .prompt import admin_router as prompt_adm
from .prompt import service_router as prompt_svc
from .quality import admin_router as quality_adm
from .quality import service_router as quality_svc
from .render_presets import admin_router as rp_adm
from .render_presets import service_router as rp_svc
from .style_profiles import admin_router as style_adm
from .style_profiles import service_router as style_svc
from .tags import admin_router as tags_adm
from .tags import service_router as tags_svc
from .voice_presets import admin_router as voice_adm
from .voice_presets import service_router as voice_svc
from .youtube import service_router as yt_svc

for _svc in [
    char_svc,
    style_svc,
    voice_svc,
    music_svc,
    bg_svc,
    tags_svc,
    quality_svc,
    yt_svc,
    prompt_svc,
    rp_svc,
    lora_svc,
]:
    service_app_router.include_router(_svc)

for _adm in [
    char_adm,
    style_adm,
    voice_adm,
    music_adm,
    bg_adm,
    tags_adm,
    quality_adm,
    prompt_adm,
    rp_adm,
    lora_adm,
]:
    admin_app_router.include_router(_adm)

__all__ = ["service_app_router", "admin_app_router"]
