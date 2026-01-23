from __future__ import annotations

import hashlib
import io
import json
import os

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image

import logic
from schemas import (
    AvatarRegenerateRequest,
    AvatarResolveRequest,
    ImageStoreRequest,
    KeywordApproveRequest,
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

# --- Routes ---

@app.get("/audio/list")
async def get_audio_list():
    logic.logger.info("📥 [Audio List]")
    files = []
    for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"):
        for f in logic.AUDIO_DIR.glob(ext):
            files.append({"name": f.name, "url": f"{logic.API_PUBLIC_URL}/assets/audio/{f.name}"})
    return {"audios": sorted(files, key=lambda x: x["name"])}


@app.post("/storyboard/create")
async def create_storyboard(request: StoryboardRequest):
    logic.logger.info("📥 [Storyboard Req] %s", request.model_dump())
    return logic.logic_create_storyboard(request)


@app.post("/scene/generate")
async def generate_scene_image(request: SceneGenerateRequest):
    logic.logger.info("📥 [Scene Gen Req] %s", request.model_dump())
    return await logic.logic_generate_scene_image(request)


@app.get("/fonts/list")
async def list_fonts():
    fonts_dir = logic.ASSETS_DIR / "fonts"
    if not fonts_dir.exists():
        return {"fonts": []}
    fonts = []
    for ext in ("*.ttf", "*.otf", "*.ttc", "*.TTF", "*.OTF", "*.TTC"):
        for path in fonts_dir.glob(ext):
            fonts.append(path.name)
    return {"fonts": sorted(set(fonts))}


@app.get("/fonts/file/{filename}")
async def get_font_file(filename: str):
    """Serve font file for browser preview."""
    from fastapi.responses import FileResponse

    fonts_dir = logic.ASSETS_DIR / "fonts"
    font_path = fonts_dir / filename
    if not font_path.exists() or not font_path.is_file():
        raise HTTPException(status_code=404, detail="Font not found")
    # Determine content type
    ext = font_path.suffix.lower()
    content_type = {
        ".ttf": "font/ttf",
        ".otf": "font/otf",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }.get(ext, "application/octet-stream")
    return FileResponse(font_path, media_type=content_type)


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


@app.get("/keywords/suggestions")
async def list_keyword_suggestions(min_count: int = 3, limit: int = 50):
    logic.logger.info("📥 [Keyword Suggestions] min_count=%s limit=%s", min_count, limit)
    suggestions = logic.load_keyword_suggestions(min_count=min_count, limit=limit)
    return {"min_count": min_count, "limit": limit, "suggestions": suggestions}


@app.get("/keywords/categories")
async def list_keyword_categories():
    logic.logger.info("📥 [Keyword Categories]")
    try:
        data = logic.load_keywords_file()
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        return {"categories": categories}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logic.logger.exception("Keyword categories load failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/keywords/approve")
async def approve_keyword(request: KeywordApproveRequest):
    logic.logger.info("📥 [Keyword Approve] %s", request.model_dump())
    tag_token = logic.normalize_prompt_token(request.tag)
    if not tag_token:
        raise HTTPException(status_code=400, detail="Invalid tag")
    category = request.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category is required")
    try:
        data = logic.load_keywords_file()
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        if category not in categories:
            raise HTTPException(status_code=400, detail="Unknown category")
        entries = categories.get(category) or []
        if not isinstance(entries, list):
            entries = []
        existing = {logic.normalize_prompt_token(item) for item in entries}
        if tag_token not in existing:
            entries.append(tag_token)
        categories[category] = entries
        data["categories"] = categories
        logic.save_keywords_file(data)
        logic.reset_keyword_cache()
        suggestions_path = logic.CACHE_DIR / "keyword_suggestions.json"
        if suggestions_path.exists():
            try:
                suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))
                if tag_token in suggestions:
                    suggestions.pop(tag_token, None)
                    suggestions_path.write_text(json.dumps(suggestions, ensure_ascii=False, indent=2))
            except Exception:
                logic.logger.exception("Failed to update keyword suggestions after approval")
        return {"ok": True, "tag": tag_token, "category": category}
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logic.logger.exception("Keyword approval failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
