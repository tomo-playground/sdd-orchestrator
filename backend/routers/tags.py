"""Tag CRUD endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import Tag
from schemas import TagCreate, TagResponse, TagSearchResponse, TagUpdate
from services.tag_classifier import TagClassifier, classify_tags_background_llm

router = APIRouter(prefix="/tags", tags=["tags"])


# === Classification Schemas ===
class ClassifyRequest(BaseModel):
    """Request for tag classification."""

    tags: list[str]


class ClassificationResultItem(BaseModel):
    """Single tag classification result."""

    group: str | None
    confidence: float
    source: str


class ClassifyResponse(BaseModel):
    """Response for tag classification."""

    results: dict[str, ClassificationResultItem]
    classified: int
    unknown: int


# === Pending Classification Schemas (15.7.5) ===


class PendingTagItem(BaseModel):
    """Tag pending classification review."""

    id: int
    name: str
    category: str | None = None
    group_name: str | None = None
    classification_source: str | None = None
    classification_confidence: float | None = None


class PendingTagsResponse(BaseModel):
    """Response for pending tags list."""

    tags: list[PendingTagItem]
    total: int


class ApproveClassificationRequest(BaseModel):
    """Request to approve/correct a tag classification."""

    tag_id: int
    group_name: str
    category: str | None = None  # Optional: update category too


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


@router.get("/search", response_model=list[TagSearchResponse])
async def search_tags(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, le=100, description="Max results"),
    category: str | None = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    """Search tags for autocomplete.

    Sorts by:
    1. Active tags first (deprecated last)
    2. Exact match (starts with query)
    3. Priority (lower is better)
    4. Name length (shorter is better)
    """
    from sqlalchemy import case, func, or_

    from services.utils import escape_like

    escaped = escape_like(q)
    query = db.query(Tag).filter(
        or_(Tag.name.ilike(f"%{escaped}%", escape="\\"), Tag.ko_name.ilike(f"%{escaped}%", escape="\\"))
    )

    if category:
        query = query.filter(Tag.category == category)

    # Calculate sort order
    active_first = case((Tag.is_active.is_(True), 0), else_=1)
    starts_with = case(
        (or_(Tag.name.ilike(f"{escaped}%", escape="\\"), Tag.ko_name.ilike(f"{escaped}%", escape="\\")), 0),
        else_=1,
    )

    query = query.order_by(
        active_first,
        starts_with,
        Tag.priority.asc(),
        func.length(Tag.name).asc(),
        Tag.name.asc(),
    )

    tags = query.limit(limit).all()

    # Map replacement_tag_name for deprecated tags
    replacement_ids = {t.replacement_tag_id for t in tags if t.replacement_tag_id}
    replacement_map: dict[int, str] = {}
    if replacement_ids:
        replacements = db.query(Tag.id, Tag.name).filter(Tag.id.in_(replacement_ids)).all()
        replacement_map = {r.id: r.name for r in replacements}

    results = []
    for tag in tags:
        data = TagSearchResponse.model_validate(tag)
        if tag.replacement_tag_id and tag.replacement_tag_id in replacement_map:
            data.replacement_tag_name = replacement_map[tag.replacement_tag_id]
        results.append(data)

    return results


# === Pending Classification Endpoints (15.7.5) ===


@router.get("/pending", response_model=PendingTagsResponse)
async def get_pending_classifications(
    source: str | None = Query(None, description="Filter by source (danbooru, llm, unknown)"),
    max_confidence: float = Query(0.9, description="Maximum confidence threshold"),
    include_unclassified: bool = Query(False, description="Include tags with group_name=NULL"),
    limit: int = Query(100, description="Maximum tags to return"),
    db: Session = Depends(get_db),
):
    """Get tags that need classification review.

    Returns tags that:
    - Were classified by Danbooru/LLM with confidence below threshold
    - Failed classification (source = 'unknown')
    - (optional) Have no group_name (unclassified)

    Does NOT include:
    - Tags with source = NULL (legacy tags with existing group_name)
    - Tags with source = 'manual' (already approved)
    - Tags with source = 'pattern' or 'rule' (high confidence from rules)
    """
    from sqlalchemy import and_, or_

    query = db.query(Tag)

    # Filter by source if specified
    if source:
        query = query.filter(Tag.classification_source == source)
    else:
        # Default: show tags needing review
        conditions = [
            # 1. Unknown source (failed to classify)
            Tag.classification_source == "unknown",
            # 2. Danbooru/LLM with low confidence
            and_(
                Tag.classification_source.in_(["danbooru", "llm"]),
                Tag.classification_confidence < max_confidence,
            ),
        ]
        # 3. Unclassified tags (group_name is NULL)
        if include_unclassified:
            conditions.append(Tag.group_name.is_(None))

        query = query.filter(or_(*conditions))

    # Order by confidence (nulls first, then low confidence)
    query = query.order_by(
        Tag.classification_confidence.is_(None).desc(),
        Tag.classification_confidence,
        Tag.name,
    )

    tags = query.limit(limit).all()

    items = [
        PendingTagItem(
            id=tag.id,
            name=tag.name,
            category=tag.category,
            group_name=tag.group_name,
            classification_source=tag.classification_source,
            classification_confidence=tag.classification_confidence,
        )
        for tag in tags
    ]

    logger.info("📋 [Tags] Listed %d pending classifications", len(items))
    return PendingTagsResponse(tags=items, total=len(items))


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int, db: Session = Depends(get_db)):
    """Get a single tag by ID."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """Create a new tag. Auto-classifies if group_name is not provided."""
    existing = db.query(Tag).filter(Tag.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag_data = data.model_dump()

    # Auto-classify if group_name not provided
    if not tag_data.get("group_name"):
        from services.keywords.patterns import suggest_category_for_tag

        suggested_group, confidence = suggest_category_for_tag(data.name)
        if suggested_group and suggested_group != "skip" and confidence > 0:
            tag_data["group_name"] = suggested_group
            tag_data["classification_source"] = tag_data.get("classification_source") or "pattern"
            tag_data["classification_confidence"] = confidence
            # Set category from group if not already set
            if not tag_data.get("category"):
                from services.tag_classifier import group_to_category

                tag_data["category"] = group_to_category(suggested_group, db)
            logger.info("🏷️ [Tags] Auto-classified '%s' → %s (%.0f%%)", data.name, suggested_group, confidence * 100)

    tag = Tag(**tag_data)
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
    # group_name → default_layer 동기화는 Tag.@validates("group_name")에서 자동 처리

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


# === Classification Endpoints (15.7) ===


@router.post("/classify", response_model=ClassifyResponse)
async def classify_tags(
    request: ClassifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Classify tags: Rules → DB (instant) + Danbooru → LLM (background).

    Steps 1-2 (Rules + DB cache) return immediately.
    Steps 3-4 (Danbooru + LLM) run in background — results available on next call.
    """
    if not request.tags:
        return ClassifyResponse(results={}, classified=0, unknown=0)

    if len(request.tags) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tags per request")

    classifier = TagClassifier(db)
    raw_results, pending_tags = classifier.classify_batch(request.tags)

    # Schedule Danbooru + LLM classification in background
    if pending_tags:
        background_tasks.add_task(classify_tags_background_llm, pending_tags)

    results = {
        tag: ClassificationResultItem(
            group=result["group"],
            confidence=result["confidence"],
            source=result["source"],
        )
        for tag, result in raw_results.items()
    }

    classified = sum(1 for r in results.values() if r.group is not None)
    unknown = len(results) - classified

    logger.info(
        "🏷️ [Tags] Classified %d/%d tags (%d unknown, %d pending background)",
        classified,
        len(request.tags),
        unknown,
        len(pending_tags),
    )

    return ClassifyResponse(results=results, classified=classified, unknown=unknown)


@router.post("/approve-classification")
async def approve_classification(request: ApproveClassificationRequest, db: Session = Depends(get_db)):
    """Approve or correct a tag's classification.

    Sets the classification source to 'manual' and confidence to 1.0.
    """
    tag = db.query(Tag).filter(Tag.id == request.tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    old_group = tag.group_name
    old_source = tag.classification_source

    # Update classification
    tag.group_name = request.group_name
    tag.classification_source = "manual"
    tag.classification_confidence = 1.0

    # Optionally update category
    if request.category:
        tag.category = request.category

    db.commit()
    db.refresh(tag)

    logger.info(
        "✅ [Tags] Approved classification: %s (%s→%s, source: %s→manual)",
        tag.name,
        old_group,
        request.group_name,
        old_source,
    )

    return {
        "ok": True,
        "tag": tag.name,
        "group_name": tag.group_name,
        "category": tag.category,
    }


@router.post("/bulk-approve-classifications")
async def bulk_approve_classifications(approvals: list[ApproveClassificationRequest], db: Session = Depends(get_db)):
    """Bulk approve multiple tag classifications."""
    if len(approvals) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 approvals per request")

    approved = []
    failed = []

    for approval in approvals:
        tag = db.query(Tag).filter(Tag.id == approval.tag_id).first()
        if not tag:
            failed.append({"tag_id": approval.tag_id, "error": "Not found"})
            continue

        tag.group_name = approval.group_name
        tag.classification_source = "manual"
        tag.classification_confidence = 1.0
        if approval.category:
            tag.category = approval.category

        approved.append(tag.name)

    db.commit()

    logger.info("✅ [Tags] Bulk approved %d classifications", len(approved))
    return {
        "ok": True,
        "approved_count": len(approved),
        "approved": approved,
        "failed": failed,
    }
