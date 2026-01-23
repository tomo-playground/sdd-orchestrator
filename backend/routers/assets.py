"""Asset management endpoints (audio, fonts)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import logic

router = APIRouter(tags=["assets"])


@router.get("/audio/list")
async def get_audio_list():
    logic.logger.info("📥 [Audio List]")
    files = []
    for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"):
        for f in logic.AUDIO_DIR.glob(ext):
            files.append({"name": f.name, "url": f"{logic.API_PUBLIC_URL}/assets/audio/{f.name}"})
    return {"audios": sorted(files, key=lambda x: x["name"])}


@router.get("/fonts/list")
async def list_fonts():
    fonts_dir = logic.ASSETS_DIR / "fonts"
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
