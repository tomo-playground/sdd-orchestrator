"""Storyboard CRUD endpoints (thin router delegating to service layer)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Storyboard
from schemas import (
    MaterialsCheckResponse,
    PaginatedStoryboardList,
    SeedAnchorRequest,
    SeedAnchorResponse,
    StatusResponse,
    StoryboardCreateResponse,  # noqa: F401
    StoryboardDetailResponse,
    StoryboardMetadataUpdateResponse,
    StoryboardRequest,
    StoryboardRestoreResponse,
    StoryboardSave,
    StoryboardSaveResponse,
    StoryboardUpdate,
    TrashedStoryboardItem,
    VerticalStatus,
)
from services.storyboard import (
    create_storyboard,
    delete_storyboard_from_db,
    get_storyboard_by_id,
    list_storyboards_from_db,
    permanent_delete_storyboard,
    save_storyboard_to_db,
    update_storyboard_in_db,
    update_storyboard_metadata,
)

router = APIRouter(prefix="/storyboards", tags=["storyboard"])
admin_router = APIRouter(prefix="/storyboards", tags=["storyboard-admin"])


@router.post("/create", response_model=StoryboardCreateResponse)
async def create_storyboard_endpoint(request: StoryboardRequest, db: Session = Depends(get_db)):
    logger.info("\U0001f4e5 [Storyboard Req] %s", request.model_dump())
    return await create_storyboard(request, db)


@router.post("", response_model=StoryboardSaveResponse)
async def save_storyboard(request: StoryboardSave, db: Session = Depends(get_db)):
    return save_storyboard_to_db(db, request)


@router.get("/trash", response_model=list[TrashedStoryboardItem])
def list_trashed_storyboards(db: Session = Depends(get_db)):
    """List soft-deleted storyboards."""
    items = (
        db.query(Storyboard)
        .filter(
            Storyboard.deleted_at.isnot(None),
        )
        .order_by(Storyboard.deleted_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None,
        }
        for s in items
    ]


@router.get("", response_model=PaginatedStoryboardList)
def list_storyboards(
    group_id: int | None = None,
    project_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return list_storyboards_from_db(db, group_id=group_id, project_id=project_id, offset=offset, limit=limit)


@router.get("/{storyboard_id}", response_model=StoryboardDetailResponse)
def get_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    return get_storyboard_by_id(db, storyboard_id)


@router.put("/{storyboard_id}", response_model=StoryboardSaveResponse)
async def update_storyboard(storyboard_id: int, request: StoryboardSave, db: Session = Depends(get_db)):
    return update_storyboard_in_db(db, storyboard_id, request)


@router.patch("/{storyboard_id}/metadata", response_model=StoryboardMetadataUpdateResponse)
async def patch_storyboard_metadata(storyboard_id: int, request: StoryboardUpdate, db: Session = Depends(get_db)):
    """Partially update storyboard metadata (title, caption, etc)."""
    return update_storyboard_metadata(db, storyboard_id, request)


@router.delete("/{storyboard_id}", response_model=StatusResponse)
async def delete_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    return delete_storyboard_from_db(db, storyboard_id)


@router.post("/{storyboard_id}/restore", response_model=StoryboardRestoreResponse)
async def restore_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted storyboard."""
    from services.storyboard import restore_storyboard_from_db

    return restore_storyboard_from_db(db, storyboard_id)


@router.get("/{storyboard_id}/materials", response_model=MaterialsCheckResponse)
def check_materials(storyboard_id: int, db: Session = Depends(get_db)):
    """Check material readiness for a storyboard."""
    from sqlalchemy import func

    from models.group import Group
    from models.scene import Scene
    from models.storyboard_character import StoryboardCharacter

    sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    scene_count = (
        db.query(func.count(Scene.id)).filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None)).scalar()
        or 0
    )

    char_count = (
        db.query(func.count(StoryboardCharacter.id)).filter(StoryboardCharacter.storyboard_id == storyboard_id).scalar()
        or 0
    )

    voice_ready = False
    music_ready = False
    if sb.group_id:
        group = db.query(Group).filter(Group.id == sb.group_id).first()
        if group:
            voice_ready = group.narrator_voice_preset_id is not None
            if group.render_preset:
                rp = group.render_preset
                music_ready = bool(rp.music_preset_id) or bool(rp.bgm_file)

    # Background: if staging started, only ready when "staged"
    stage = sb.stage_status
    if stage and stage not in ("pending",):
        bg_ready = stage == "staged"
        bg_detail = "Staged" if bg_ready else f"Stage: {stage}"
    else:
        bg_ready = True
        bg_detail = "Optional"

    return MaterialsCheckResponse(
        storyboard_id=storyboard_id,
        script=VerticalStatus(ready=scene_count > 0, count=scene_count),
        characters=VerticalStatus(ready=char_count > 0, count=char_count),
        voice=VerticalStatus(ready=voice_ready),
        music=VerticalStatus(ready=music_ready),
        background=VerticalStatus(ready=bg_ready, detail=bg_detail),
    )


@router.post("/{storyboard_id}/seed", response_model=SeedAnchorResponse)
async def set_storyboard_seed(
    storyboard_id: int,
    request: SeedAnchorRequest,
    db: Session = Depends(get_db),
):
    """Set or clear the base seed for consistent scene generation.

    base_seed: null → auto-generate, 0 → clear, positive → set explicitly.
    """
    from services.seed_anchoring import set_storyboard_base_seed

    sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    final_seed = set_storyboard_base_seed(storyboard_id, request.base_seed, db)
    return SeedAnchorResponse(
        storyboard_id=storyboard_id,
        base_seed=final_seed,
        anchored=final_seed is not None,
    )


@admin_router.delete("/{storyboard_id}/permanent", response_model=StatusResponse)
async def permanently_delete_storyboard(storyboard_id: int, db: Session = Depends(get_db)):
    """Permanently delete a storyboard and all associated assets."""
    return permanent_delete_storyboard(db, storyboard_id)
