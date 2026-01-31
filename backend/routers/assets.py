"""Asset management endpoints (audio, fonts)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import API_PUBLIC_URL, ASSETS_DIR, AUDIO_DIR, logger

router = APIRouter(tags=["assets"])


@router.get("/audio/list")
async def get_audio_list():
    logger.info("📥 [Audio List]")
    from config import STORAGE_MODE
    from services.storage import get_storage
    storage = get_storage()

    files = []
    if STORAGE_MODE == "s3":
        # List from S3/MinIO
        prefix = "shared/audio/"
        all_keys = storage.list_prefix(prefix)
        for key in all_keys:
            if key.lower().endswith((".mp3", ".wav", ".m4a")):
                name = key.replace(prefix, "", 1)
                files.append({"name": name, "url": storage.get_url(key)})
    else:
        # List from Local filesystem
        for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"):
            for f in AUDIO_DIR.glob(ext):
                files.append({"name": f.name, "url": f"{API_PUBLIC_URL}/assets/audio/{f.name}"})
    
    return {"audios": sorted(files, key=lambda x: x["name"])}


@router.get("/fonts/list")
async def list_fonts():
    from config import STORAGE_MODE
    from services.storage import get_storage
    storage = get_storage()

    fonts = []
    if STORAGE_MODE == "s3":
        prefix = "shared/fonts/"
        all_keys = storage.list_prefix(prefix)
        for key in all_keys:
            if key.lower().endswith((".ttf", ".otf", ".ttc")):
                name = key.replace(prefix, "", 1)
                fonts.append({"name": name})
    else:
        fonts_dir = ASSETS_DIR / "fonts"
        if not fonts_dir.exists():
            return {"fonts": []}
        for ext in ("*.ttf", "*.otf", "*.ttc", "*.TTF", "*.OTF", "*.TTC"):
            for path in fonts_dir.glob(ext):
                fonts.append({"name": path.name})

    # Sort by name and remove duplicates
    unique_fonts = {f["name"]: f for f in fonts}.values()
    return {"fonts": sorted(unique_fonts, key=lambda x: x["name"])}


@router.get("/fonts/file/{filename}")
async def get_font_file(filename: str):
    """Serve font file for browser preview."""
    from config import STORAGE_MODE
    from services.storage import get_storage
    storage = get_storage()

    if STORAGE_MODE == "s3":
        storage_key = f"shared/fonts/{filename}"
        if not storage.exists(storage_key):
            raise HTTPException(status_code=404, detail="Font not found in storage")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(storage.get_url(storage_key))
    
    fonts_dir = ASSETS_DIR / "fonts"
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


@router.get("/overlay/list")
async def list_overlays():
    """List available overlay frame styles."""
    from config import STORAGE_MODE
    from services.storage import get_storage
    storage = get_storage()

    overlays = []
    if STORAGE_MODE == "s3":
        prefix = "shared/overlay/"
        all_keys = storage.list_prefix(prefix)
        for key in all_keys:
            if key.lower().endswith((".png", ".jpg", ".jpeg")):
                filename = key.replace(prefix, "", 1)
                name = filename.replace("overlay_", "").replace(".png", "").replace(".jpg", "").replace("_", " ").title()
                overlays.append({
                    "id": filename,
                    "name": name,
                    "url": storage.get_url(key)
                })
    else:
        overlay_dir = ASSETS_DIR / "overlay"
        if not overlay_dir.exists():
            return {"overlays": []}
        for ext in ("*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg", "*.JPEG"):
            for path in overlay_dir.glob(ext):
                overlays.append({
                    "id": path.name,
                    "name": path.stem.replace("overlay_", "").replace("_", " ").title(),
                    "url": f"{API_PUBLIC_URL}/assets/overlay/{path.name}"
                })
    return {"overlays": sorted(overlays, key=lambda x: x["name"])}


@router.get("/assets/overlay/{filename}")
async def get_overlay_file(filename: str):
    """Serve overlay frame image."""
    from config import STORAGE_MODE
    from services.storage import get_storage
    storage = get_storage()

    if STORAGE_MODE == "s3":
        storage_key = f"shared/overlay/{filename}"
        if not storage.exists(storage_key):
            raise HTTPException(status_code=404, detail="Overlay not found in storage")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(storage.get_url(storage_key))

    overlay_dir = ASSETS_DIR / "overlay"
    overlay_path = overlay_dir / filename
    if not overlay_path.exists() or not overlay_path.is_file():
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(overlay_path, media_type="image/png")
