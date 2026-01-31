"""Avatar generation and resolution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from schemas import AvatarRegenerateRequest, AvatarResolveRequest
from services.avatar import avatar_filename, ensure_avatar_file
from services.storage import get_storage

router = APIRouter(prefix="/avatar", tags=["avatar"])


@router.post("/regenerate")
async def regenerate_avatar(request: AvatarRegenerateRequest):
    storage = get_storage()
    avatar_key = request.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="Avatar key is required")
    filename = avatar_filename(avatar_key)
    storage_key = f"shared/avatars/{filename}"
    if storage.exists(storage_key):
        storage.delete(storage_key)

    regenerated_key = await ensure_avatar_file(avatar_key)
    if not regenerated_key:
        raise HTTPException(status_code=500, detail="Avatar regeneration failed")

    # Return JUST the filename for UI compatibility, or key if UI is updated
    # In V3, ensure_avatar_file returns storage_key
    # UI expected filename like 'avatar_...png', we'll give it that or the key.
    # We'll use the basename for UI compatibility if needed
    from pathlib import Path
    return {"filename": Path(regenerated_key).name}


@router.post("/resolve")
async def resolve_avatar(request: AvatarResolveRequest):
    storage = get_storage()
    avatar_key = request.avatar_key.strip()
    if not avatar_key:
        raise HTTPException(status_code=400, detail="Avatar key is required")
    filename = avatar_filename(avatar_key)
    storage_key = f"shared/avatars/{filename}"
    if not storage.exists(storage_key):
        return {"filename": None}
    return {"filename": filename}
