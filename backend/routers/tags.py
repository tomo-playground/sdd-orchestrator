"""Tag CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Tag
from schemas import TagCreate, TagResponse, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    category: str | None = Query(None, description="Filter by category"),
    group_name: str | None = Query(None, description="Filter by group"),
    db: Session = Depends(get_db),
):
    """List all tags with optional filtering."""
    query = db.query(Tag)
    if category:
        query = query.filter(Tag.category == category)
    if group_name:
        query = query.filter(Tag.group_name == group_name)
    tags = query.order_by(Tag.priority, Tag.name).all()
    logger.info("📋 [Tags] Listed %d tags", len(tags))
    return tags


@router.get("/groups")
async def list_tag_groups(db: Session = Depends(get_db)):
    """List all unique group names with counts."""
    from sqlalchemy import func

    results = (
        db.query(Tag.category, Tag.group_name, func.count(Tag.id).label("count"))
        .group_by(Tag.category, Tag.group_name)
        .order_by(Tag.category, Tag.group_name)
        .all()
    )
    groups = [{"category": r.category, "group_name": r.group_name, "count": r.count} for r in results]
    return {"groups": groups}


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int, db: Session = Depends(get_db)):
    """Get a single tag by ID."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """Create a new tag."""
    existing = db.query(Tag).filter(Tag.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(**data.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    logger.info("✅ [Tags] Created: %s", tag.name)
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: int, data: TagUpdate, db: Session = Depends(get_db)):
    """Update an existing tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tag, key, value)

    db.commit()
    db.refresh(tag)
    logger.info("✏️ [Tags] Updated: %s", tag.name)
    return tag


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """Delete a tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    name = tag.name
    db.delete(tag)
    db.commit()
    logger.info("🗑️ [Tags] Deleted: %s", name)
    return {"ok": True, "deleted": name}
