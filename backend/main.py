from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import ASSETS_DIR
from routers import (
    assets_router,
    avatar_router,
    characters_router,
    cleanup_router,
    keywords_router,
    loras_router,
    presets_router,
    prompt_router,
    scene_router,
    sd_models_router,
    sd_router,
    storyboard_router,
    style_profiles_router,
    tags_router,
    video_router,
)

# --- App Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# --- Routers ---
app.include_router(assets_router)
app.include_router(avatar_router)
app.include_router(characters_router)
app.include_router(cleanup_router)
app.include_router(keywords_router)
app.include_router(loras_router)
app.include_router(presets_router)
app.include_router(prompt_router)
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
