"""Avatar generation and resolution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import AVATAR_DIR
from schemas import AvatarRegenerateRequest, AvatarResolveRequest
from services.avatar import avatar_filename, ensure_avatar_file

router = APIRouter(prefix="/avatar", tags=["avatar"])


@router.post("/regenerate")
async def regenerate_avatar(request: AvatarRegenerateRequest):
    avatar_key = request.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="Avatar key is required")
    filename = avatar_filename(avatar_key)
    target = AVATAR_DIR / filename
    if target.exists():
        target.unlink()
    regenerated = await ensure_avatar_file(avatar_key)
    if not regenerated:
        raise HTTPException(status_code=500, detail="Avatar regeneration failed")
    return {"filename": regenerated}


@router.post("/resolve")
async def resolve_avatar(request: AvatarResolveRequest):
    avatar_key = request.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="Avatar key is required")
    filename = avatar_filename(avatar_key)
    target = AVATAR_DIR / filename
    if not target.exists():
        return {"filename": None}
    return {"filename": filename}
