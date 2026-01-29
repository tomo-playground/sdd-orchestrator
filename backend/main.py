from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import ASSETS_DIR
from routers import (
    admin_router,
    assets_router,
    avatar_router,
    characters_router,
    cleanup_router,
    controlnet_router,
    evaluation_router,
    generation_logs_router,
    keywords_router,
    loras_router,
    presets_router,
    prompt_router,
    prompt_histories_router,
    quality_router,
    scene_router,
    sd_models_router,
    sd_router,
    storyboard_router,
    style_profiles_router,
    tags_router,
    video_router,
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    from database import get_db, engine
    from models.base import Base
    from services.keywords.db_cache import TagCategoryCache, TagAliasCache, TagRuleCache, LoRATriggerCache
    from services.keywords.core import TagFilterCache
    from config import logger
    
    # Ensure database tables exist
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
        
    logger.info("🚀 [Startup] Application started successfully")
    
    yield
    
    # Shutdown logic (if any)
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
import os
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# --- Routers ---
app.include_router(admin_router)
app.include_router(assets_router)
app.include_router(avatar_router)
app.include_router(characters_router)
app.include_router(cleanup_router)
app.include_router(controlnet_router)
app.include_router(evaluation_router)
app.include_router(generation_logs_router)
app.include_router(keywords_router)
app.include_router(loras_router)
app.include_router(presets_router)
app.include_router(prompt_router)
app.include_router(prompt_histories_router)
app.include_router(quality_router)
app.include_router(scene_router)
app.include_router(sd_models_router)
app.include_router(sd_router)
app.include_router(storyboard_router)
app.include_router(style_profiles_router)
app.include_router(tags_router)
app.include_router(video_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
