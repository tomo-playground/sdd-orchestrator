"""Stage Workflow API — background generation, status, assignment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from config import STAGE_STATUS_STAGING
from database import get_db
from models.background import Background
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import (
    BgmPrebuildRequest,
    BgmPrebuildResponse,
    StageAssignResponse,
    StageGenerateResponse,
    StageLocationStatus,
    StageRegenerateRequest,
    StageRegenerateResponse,
    StageStatusResponse,
)

router = APIRouter(prefix="/storyboards", tags=["stage"])


def _get_storyboard_or_404(storyboard_id: int, db: Session) -> Storyboard:
    sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not sb:
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return sb


@router.post(
    "/{storyboard_id}/stage/generate-backgrounds",
    response_model=StageGenerateResponse,
)
async def generate_backgrounds(
    storyboard_id: int,
    force: bool = Query(False, description="If true, regenerate even if image already exists"),
    db: Session = Depends(get_db),
):
    """Generate no_humans background images for each location."""
    sb = _get_storyboard_or_404(storyboard_id, db)
    if sb.stage_status == STAGE_STATUS_STAGING:
        raise HTTPException(status_code=409, detail="Background generation already in progress")

    from services.stage.background_generator import generate_location_backgrounds

    try:
        results = await generate_location_backgrounds(storyboard_id, db, force=force)
    except ValueError as e:
        from services.error_responses import raise_user_error

        raise_user_error("stage_generate", e, status_code=404)
        raise  # unreachable; satisfies type checker

    return StageGenerateResponse(storyboard_id=storyboard_id, results=results)


@router.get(
    "/{storyboard_id}/stage/status",
    response_model=StageStatusResponse,
)
def get_stage_status(storyboard_id: int, db: Session = Depends(get_db)):
    """Get current stage status with location details."""
    sb = _get_storyboard_or_404(storyboard_id, db)

    scenes = (
        db.query(Scene)
        .filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )
    backgrounds = (
        db.query(Background)
        .options(joinedload(Background.image_asset))
        .filter(Background.storyboard_id == storyboard_id, Background.deleted_at.is_(None))
        .all()
    )

    bg_map: dict[str, Background] = {}
    for bg in backgrounds:
        if bg.location_key:
            bg_map[bg.location_key] = bg

    # Derive locations from scenes
    from services.stage.background_generator import extract_locations_from_scenes

    loc_data = extract_locations_from_scenes(scenes, db)

    locations: list[StageLocationStatus] = []
    ready_count = 0

    for loc_key, info in loc_data.items():
        bg = bg_map.get(loc_key)
        has_image = bool(bg and bg.image_asset_id)
        if has_image:
            ready_count += 1
        locations.append(
            StageLocationStatus(
                location_key=loc_key,
                background_id=bg.id if bg else None,
                image_url=bg.image_url if bg else None,
                tags=info["tags"],
                scene_ids=info["scene_ids"],
                has_image=has_image,
                style_profile_id=bg.style_profile_id if bg else None,
            )
        )

    return StageStatusResponse(
        storyboard_id=storyboard_id,
        stage_status=sb.stage_status,
        locations=locations,
        total=len(locations),
        ready=ready_count,
    )


@router.post(
    "/{storyboard_id}/stage/assign-backgrounds",
    response_model=StageAssignResponse,
)
def assign_backgrounds(storyboard_id: int, db: Session = Depends(get_db)):
    """Assign generated backgrounds to matching scenes."""
    _get_storyboard_or_404(storyboard_id, db)

    from services.stage.background_generator import assign_backgrounds_to_scenes

    assignments = assign_backgrounds_to_scenes(storyboard_id, db)
    return StageAssignResponse(assignments=assignments)


@router.post(
    "/{storyboard_id}/stage/regenerate-background/{location_key}",
    response_model=StageRegenerateResponse,
)
async def regenerate_background_endpoint(
    storyboard_id: int,
    location_key: str,
    body: StageRegenerateRequest | None = None,
    db: Session = Depends(get_db),
):
    """Regenerate a specific location's background image. Optionally update tags first."""
    _get_storyboard_or_404(storyboard_id, db)

    from services.stage.background_generator import regenerate_background

    new_tags = body.tags if body else None
    try:
        result = await regenerate_background(storyboard_id, location_key, db, tags=new_tags)
    except ValueError as e:
        from services.error_responses import raise_user_error

        raise_user_error("stage_regenerate", e, status_code=404)
        raise  # unreachable; satisfies type checker

    return StageRegenerateResponse(**result)


@router.post(
    "/{storyboard_id}/stage/bgm-prebuild",
    response_model=BgmPrebuildResponse,
)
async def bgm_prebuild(
    storyboard_id: int,
    body: BgmPrebuildRequest | None = None,
    db: Session = Depends(get_db),
):
    """Pre-generate BGM audio for storyboard during Stage phase."""
    from services.bgm_prebuild import prebuild_bgm

    prompt = body.bgm_prompt if body else None
    return await prebuild_bgm(storyboard_id, prompt, db)
