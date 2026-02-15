from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import (
    activity_logs_router,
    admin_router,
    analytics_router,
    assets_router,
    avatar_router,
    backgrounds_router,
    characters_router,
    cleanup_router,
    controlnet_router,
    creative_presets_router,
    creative_router,
    groups_router,
    keywords_router,
    lab_router,
    loras_router,
    memory_router,
    music_presets_router,
    presets_router,
    projects_router,
    prompt_histories_router,
    prompt_router,
    quality_router,
    render_presets_router,
    scene_router,
    scripts_router,
    sd_models_router,
    sd_router,
    settings_router,
    storyboard_router,
    style_profiles_router,
    tags_router,
    video_router,
    voice_presets_router,
    youtube_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    # Validate storage credentials before initialization
    from config import logger, validate_storage_config
    from database import engine, get_db
    from models.base import Base
    from services.keywords.core import TagFilterCache
    from services.keywords.db_cache import LoRATriggerCache, TagAliasCache, TagCategoryCache, TagRuleCache
    from services.storage import initialize_storage

    validate_storage_config()

    # Initialize Storage Service
    initialize_storage()

    # Ensure repository assets are in shared storage
    from services.asset_service import AssetService

    AssetService.ensure_shared_assets()
    Base.metadata.create_all(bind=engine)

    # Initialize Tag Caches
    db = next(get_db())
    try:
        TagCategoryCache.initialize(db)
        TagFilterCache.initialize(db)
        TagAliasCache.initialize(db)
        TagRuleCache.initialize(db)
        TagRuleCache.initialize(db)
        LoRATriggerCache.initialize(db)

        # Self-Correction: Apply high-confidence tag suggestions
        from services.keywords.suggestions import apply_high_confidence_suggestions

        applied = apply_high_confidence_suggestions()
        if applied > 0:
            logger.info(f"✅ [Self-Correction] Auto-classified {applied} tags on startup")

    except Exception as e:
        logger.error(f"Failed to initialize tag caches or self-correct: {e}")
    finally:
        db.close()

    # TTS Model Eager Loading (required for video rendering)
    from services.video.scene_processing import get_qwen_model

    logger.info("[TTS] Loading Qwen3-TTS model...")
    get_qwen_model()
    logger.info("[TTS] Qwen3-TTS model loaded successfully")

    # Initialize LangGraph Checkpointer + Store
    from services.agent.checkpointer import close_checkpointer, get_checkpointer
    from services.agent.store import close_store, get_store

    await get_checkpointer()
    await get_store()

    logger.info("🚀 [Startup] Application started successfully")

    yield

    # Shutdown logic
    from services.agent.observability import flush_langfuse

    flush_langfuse()
    await close_store()
    await close_checkpointer()
    logger.info("🛑 [Shutdown] Application execution finished")


# --- App Setup ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Static Files ---
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# --- Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- Routers ---
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(assets_router)
app.include_router(avatar_router)
app.include_router(backgrounds_router)
app.include_router(characters_router)
app.include_router(cleanup_router)
app.include_router(controlnet_router)
app.include_router(groups_router)
app.include_router(projects_router)
app.include_router(activity_logs_router)
app.include_router(keywords_router)
app.include_router(lab_router)
app.include_router(creative_router)
app.include_router(creative_presets_router)
app.include_router(loras_router)
app.include_router(memory_router)
app.include_router(presets_router)
app.include_router(prompt_router)
app.include_router(prompt_histories_router)
app.include_router(quality_router)
app.include_router(render_presets_router)
app.include_router(scene_router)
app.include_router(scripts_router)
app.include_router(sd_models_router)
app.include_router(sd_router)
app.include_router(settings_router)
app.include_router(storyboard_router)
app.include_router(style_profiles_router)
app.include_router(tags_router)
app.include_router(video_router)
app.include_router(voice_presets_router)
app.include_router(music_presets_router)
app.include_router(youtube_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
