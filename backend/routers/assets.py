"""Asset management endpoints (audio, fonts)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import API_PUBLIC_URL, ASSETS_DIR, AUDIO_DIR, logger

router = APIRouter(tags=["assets"])


@router.get("/audio/list")
async def get_audio_list():
    logger.info("📥 [Audio List]")
    files = []
    for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"):
        for f in AUDIO_DIR.glob(ext):
            files.append({"name": f.name, "url": f"{API_PUBLIC_URL}/assets/audio/{f.name}"})
    return {"audios": sorted(files, key=lambda x: x["name"])}


@router.get("/fonts/list")
async def list_fonts():
    fonts_dir = ASSETS_DIR / "fonts"
    if not fonts_dir.exists():
        return {"fonts": []}
    fonts = []
    for ext in ("*.ttf", "*.otf", "*.ttc", "*.TTF", "*.OTF", "*.TTC"):
        for path in fonts_dir.glob(ext):
            fonts.append(path.name)
    return {"fonts": sorted(set(fonts))}


@router.get("/fonts/file/{filename}")
async def get_font_file(filename: str):
    """Serve font file for browser preview."""
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
    overlay_dir = ASSETS_DIR / "overlay"
    if not overlay_dir.exists():
        return {"overlays": []}
    overlays = []
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
    overlay_dir = ASSETS_DIR / "overlay"
    overlay_path = overlay_dir / filename
    if not overlay_path.exists() or not overlay_path.is_file():
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(overlay_path, media_type="image/png")
