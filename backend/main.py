from __future__ import annotations

import hashlib
import io
import os

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image

import logic
from routers import assets_router, keywords_router
from schemas import (
    AvatarRegenerateRequest,
    AvatarResolveRequest,
    ImageStoreRequest,
    PromptRewriteRequest,
    PromptSplitRequest,
    SceneGenerateRequest,
    SceneValidateRequest,
    SDModelRequest,
    StoryboardRequest,
    VideoDeleteRequest,
    VideoRequest,
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
app.mount("/assets", StaticFiles(directory=str(logic.ASSETS_DIR)), name="assets")

# --- Routers ---
app.include_router(assets_router)
app.include_router(keywords_router)

# --- Routes ---


@app.post("/storyboard/create")
async def create_storyboard(request: StoryboardRequest):
    logic.logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return logic.logic_create_storyboard(request)


@app.post("/scene/generate")
async def generate_scene_image(request: SceneGenerateRequest):
    logic.logger.info("📥 [Scene Gen Req] %s", request.model_dump())
    return await logic.logic_generate_scene_image(request)


@app.post("/image/store")
async def store_scene_image(request: ImageStoreRequest):
    try:
        image_bytes = logic.decode_data_url(request.image_b64)
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc
    digest = hashlib.sha1(image_bytes).hexdigest()[:16]
    store_dir = logic.IMAGE_DIR / "stored"
    store_dir.mkdir(parents=True, exist_ok=True)
    filename = f"scene_{digest}.png"
    target = store_dir / filename
    if not target.exists():
        image = image.convert("RGBA")
        image.save(target, format="PNG")
    return {"url": f"{logic.API_PUBLIC_URL}/outputs/images/stored/{filename}"}


@app.post("/scene/validate_image")
async def validate_scene_image(request: SceneValidateRequest):
    logic.logger.info("📥 [Scene Validate Req] %s", logic.scrub_payload(request.model_dump()))
    return logic.logic_validate_scene_image(request)


@app.post("/prompt/rewrite")
async def rewrite_prompt(request: PromptRewriteRequest):
    logic.logger.info("📥 [Prompt Rewrite Req] %s", request.model_dump())
    return logic.logic_rewrite_prompt(request)


@app.post("/prompt/split")
async def split_prompt(request: PromptSplitRequest):
    logic.logger.info("📥 [Prompt Split Req] %s", request.model_dump())
    return logic.logic_split_prompt(request)


@app.get("/sd/models")
async def list_sd_models():
    logic.logger.info("📥 [SD Models]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(logic.SD_MODELS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"models": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD models fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/sd/options")
async def get_sd_options():
    logic.logger.info("📥 [SD Options]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(logic.SD_OPTIONS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, dict):
                return {"options": data, "model": data.get("sd_model_checkpoint", "Unknown")}
            return {"options": {}, "model": "Unknown"}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD options fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/sd/options")
async def update_sd_options(request: SDModelRequest):
    logic.logger.info("📥 [SD Options Update] %s", request.model_dump())
    payload = {"sd_model_checkpoint": request.sd_model_checkpoint}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(logic.SD_OPTIONS_URL, json=payload, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"ok": True, "model": data.get("sd_model_checkpoint", request.sd_model_checkpoint)}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD options update failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/sd/loras")
async def list_sd_loras():
    logic.logger.info("📥 [SD LoRAs]")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(logic.SD_LORAS_URL, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            return {"loras": data if isinstance(data, list) else []}
    except httpx.HTTPError as exc:
        logic.logger.exception("SD LoRAs fetch failed")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/video/create")
async def create_video(request: VideoRequest):
    logic.logger.info("📥 [Video Req] %s", logic.scrub_payload(request.model_dump()))
    return await logic.logic_create_video(request)


@app.post("/video/delete")
async def delete_video(request: VideoDeleteRequest):
    filename = os.path.basename(request.filename or "")
    if not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    target = logic.VIDEO_DIR / filename
    if not target.exists():
        return {"ok": False, "deleted": False, "reason": "not_found"}
    try:
        target.unlink()
        return {"ok": True, "deleted": True}
    except Exception as exc:
        logic.logger.exception("Video delete failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/video/exists")
async def video_exists(filename: str = Query(..., min_length=1)):
    name = os.path.basename(filename)
    if not name.endswith(".mp4"):
        return {"exists": False}
    target = logic.VIDEO_DIR / name
    return {"exists": target.exists()}


@app.post("/avatar/regenerate")
async def regenerate_avatar(request: AvatarRegenerateRequest):
    avatar_key = request.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="Avatar key is required")
    filename = logic.avatar_filename(avatar_key)
    target = logic.AVATAR_DIR / filename
    if target.exists():
        target.unlink()
    regenerated = await logic.ensure_avatar_file(avatar_key)
    if not regenerated:
        raise HTTPException(status_code=500, detail="Avatar regeneration failed")
    return {"filename": regenerated}


@app.post("/avatar/resolve")
async def resolve_avatar(request: AvatarResolveRequest):
    avatar_key = request.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="Avatar key is required")
    filename = logic.avatar_filename(avatar_key)
    target = logic.AVATAR_DIR / filename
    if not target.exists():
        return {"filename": None}
    return {"filename": filename}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
