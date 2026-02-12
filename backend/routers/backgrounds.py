"""Background asset library CRUD endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models.background import Background
from models.media_asset import MediaAsset
from schemas import BackgroundCreate, BackgroundResponse, BackgroundUpdate
from services.asset_service import AssetService

router = APIRouter(prefix="/backgrounds", tags=["backgrounds"])


def _bg_to_response(bg: Background, db: Session) -> dict:
    """Build response dict with computed image_url."""
    image_url = None
    if bg.image_asset_id:
        asset = db.get(MediaAsset, bg.image_asset_id)
        if asset:
            image_url = asset.url
    return {
        "id": bg.id,
        "name": bg.name,
        "description": bg.description,
        "image_url": image_url,
        "image_asset_id": bg.image_asset_id,
        "tags": bg.tags,
        "category": bg.category,
        "weight": bg.weight,
        "is_system": bg.is_system,
        "created_at": bg.created_at,
    }


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    """List distinct categories in use."""
    rows = (
        db.query(Background.category)
        .filter(Background.deleted_at.is_(None), Background.category.isnot(None))
        .distinct()
        .order_by(Background.category)
        .all()
    )
    return [r[0] for r in rows]


@router.get("", response_model=list[BackgroundResponse])
def list_backgrounds(
    search: str | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List backgrounds with optional search and category filter."""
    q = db.query(Background).filter(Background.deleted_at.is_(None))
    if category:
        q = q.filter(Background.category == category)
    if search:
        pattern = f"%{search}%"
        q = q.filter(Background.name.ilike(pattern))
    backgrounds = q.order_by(Background.id.desc()).all()
    return [_bg_to_response(bg, db) for bg in backgrounds]


@router.get("/{background_id}", response_model=BackgroundResponse)
def get_background(background_id: int, db: Session = Depends(get_db)):
    bg = db.query(Background).filter(Background.id == background_id, Background.deleted_at.is_(None)).first()
    if not bg:
        raise HTTPException(status_code=404, detail="Background not found")
    return _bg_to_response(bg, db)


@router.post("", response_model=BackgroundResponse, status_code=201)
def create_background(body: BackgroundCreate, db: Session = Depends(get_db)):
    bg = Background(**body.model_dump(exclude_unset=True), is_system=False)
    db.add(bg)
    db.commit()
    db.refresh(bg)
    return _bg_to_response(bg, db)


@router.put("/{background_id}", response_model=BackgroundResponse)
def update_background(
    background_id: int,
    body: BackgroundUpdate,
    db: Session = Depends(get_db),
):
    bg = db.query(Background).filter(Background.id == background_id, Background.deleted_at.is_(None)).first()
    if not bg:
        raise HTTPException(status_code=404, detail="Background not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(bg, key, value)
    db.commit()
    db.refresh(bg)
    return _bg_to_response(bg, db)


@router.delete("/{background_id}")
def delete_background(background_id: int, db: Session = Depends(get_db)):
    """Soft delete a background."""
    bg = db.query(Background).filter(Background.id == background_id, Background.deleted_at.is_(None)).first()
    if not bg:
        raise HTTPException(status_code=404, detail="Background not found")
    bg.deleted_at = datetime.now(UTC)
    db.commit()
    return {"ok": True, "deleted": bg.name}


@router.post("/{background_id}/restore", response_model=BackgroundResponse)
def restore_background(background_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted background."""
    bg = db.query(Background).filter(Background.id == background_id, Background.deleted_at.isnot(None)).first()
    if not bg:
        raise HTTPException(status_code=404, detail="Background not found or not deleted")
    bg.deleted_at = None
    db.commit()
    db.refresh(bg)
    return _bg_to_response(bg, db)


@router.post("/{background_id}/upload-image", response_model=BackgroundResponse)
async def upload_background_image(
    background_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """Upload a reference image for a background."""
    bg = db.query(Background).filter(Background.id == background_id, Background.deleted_at.is_(None)).first()
    if not bg:
        raise HTTPException(status_code=404, detail="Background not found")

    from services.upload_validation import validate_image_upload

    image_bytes = await validate_image_upload(file)
    mime = file.content_type or "image/png"
    svc = AssetService(db)
    asset = svc.save_background_image(bg.id, image_bytes, mime)
    bg.image_asset_id = asset.id
    db.commit()
    db.refresh(bg)
    return _bg_to_response(bg, db)
