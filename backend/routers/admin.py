"""Admin endpoints for database management and media asset GC."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Tag, TagRule
from services.media_gc import MediaGCService

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================
# Pydantic Schemas
# ============================================================

class DeprecateTagRequest(BaseModel):
    """Request schema for deprecating a tag."""
    deprecated_reason: str
    replacement_tag_id: int | None = None


@router.post("/migrate-tag-rules")
async def migrate_tag_conflict_rules(db: Session = Depends(get_db)):
    """Migrate hardcoded tag conflict rules to database.

    This is a one-time migration endpoint to populate tag_rules table
    with conflict pairs that were previously hardcoded in prompt_composition.py.
    """

    # List of conflicting pairs to migrate
    conflicts = [
        # Expression conflicts
        ('crying', 'laughing'), ('crying', 'happy'), ('crying', 'smile'),
        ('sad', 'happy'), ('sad', 'smile'), ('sad', 'laughing'),
        ('angry', 'happy'), ('angry', 'smile'),
        # Gaze conflicts
        ('looking_down', 'looking_up'), ('looking_away', 'looking_at_viewer'),
        ('closed_eyes', 'looking_at_viewer'),
        # Pose conflicts
        ('sitting', 'standing'), ('lying', 'standing'), ('lying', 'sitting'),
    ]

    added = []
    skipped = []
    errors = []

    for s_name, t_name in conflicts:
        try:
            # Find tags
            s_tag = db.query(Tag).filter(Tag.name == s_name).first()
            t_tag = db.query(Tag).filter(Tag.name == t_name).first()

            if not s_tag or not t_tag:
                errors.append(f"Tag not found: {s_name} or {t_name}")
                continue

            # Check if rule already exists
            exists = db.query(TagRule).filter(
                TagRule.source_tag_id == s_tag.id,
                TagRule.target_tag_id == t_tag.id,
                TagRule.rule_type == 'conflict'
            ).first()

            if not exists:
                # Also check reverse direction
                reverse_exists = db.query(TagRule).filter(
                    TagRule.source_tag_id == t_tag.id,
                    TagRule.target_tag_id == s_tag.id,
                    TagRule.rule_type == 'conflict'
                ).first()

                if not reverse_exists:
                    rule = TagRule(
                        source_tag_id=s_tag.id,
                        target_tag_id=t_tag.id,
                        rule_type='conflict',
                        message='Conflicting tags',
                        active=True
                    )
                    db.add(rule)
                    added.append(f"{s_name} <-> {t_name}")
                else:
                    skipped.append(f"{s_name} <-> {t_name} (reverse exists)")
            else:
                skipped.append(f"{s_name} <-> {t_name} (already exists)")

        except Exception as e:
            errors.append(f"Error processing {s_name} <-> {t_name}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "added": added,
            "skipped": skipped,
            "errors": errors
        }

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total_added": len(added),
        "total_skipped": len(skipped),
        "total_errors": len(errors)
    }


@router.post("/migrate-category-rules")
async def migrate_category_conflict_rules(db: Session = Depends(get_db)):
    """DEPRECATED (Phase 6-4.26): Category-level conflicts removed.

    Category-level conflict rules were removed because:
    - Never used (0/16 rules in production)
    - Logically unnecessary (tag-level conflicts are sufficient)
    - Group-level conflicts (if needed) should be handled differently

    Use tag-level conflicts instead (/activity-logs/apply-conflict-rules).
    """
    return {
        "success": False,
        "error": "Category-level conflicts deprecated in Phase 6-4.26",
        "reason": "Never used (0/16 rules), logically unnecessary",
        "migration": "Use tag-level conflicts via /activity-logs/apply-conflict-rules",
        "deprecated_in": "Phase 6-4.26",
    }


@router.post("/refresh-caches")
async def refresh_all_caches(db: Session = Depends(get_db)):
    """Refresh all in-memory caches from database.

    Call this after migrating data to ensure caches are up-to-date.
    """
    from services.keywords.core import TagFilterCache
    from services.keywords.db_cache import (
        LoRATriggerCache,
        TagAliasCache,
        TagCategoryCache,
        TagRuleCache,
    )

    try:
        TagCategoryCache.refresh(db)
        TagFilterCache.refresh(db)
        TagAliasCache.refresh(db)
        TagRuleCache.refresh(db)
        LoRATriggerCache.refresh(db)

        return {
            "success": True,
            "message": "All caches refreshed successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# Tag Deprecation Management (Phase 6-4.15.8)
# ============================================================

@router.get("/tags/deprecated")
async def get_deprecated_tags(db: Session = Depends(get_db)):
    """Get all deprecated tags with their replacement information."""
    deprecated_tags = db.query(Tag).filter(Tag.is_active.is_(False)).all()

    result = []
    for tag in deprecated_tags:
        replacement = None
        if tag.replacement_tag_id:
            replacement_tag = db.query(Tag).filter(Tag.id == tag.replacement_tag_id).first()
            if replacement_tag:
                replacement = {
                    "id": replacement_tag.id,
                    "name": replacement_tag.name,
                    "category": replacement_tag.category
                }

        result.append({
            "id": tag.id,
            "name": tag.name,
            "category": tag.category,
            "deprecated_reason": tag.deprecated_reason,
            "replacement": replacement,
            "created_at": tag.created_at.isoformat() if tag.created_at else None,
            "updated_at": tag.updated_at.isoformat() if tag.updated_at else None
        })

    return {
        "total": len(result),
        "tags": result
    }


@router.put("/tags/{tag_id}/deprecate")
async def deprecate_tag(
    tag_id: int,
    request: DeprecateTagRequest,
    db: Session = Depends(get_db)
):
    """Deprecate a tag and optionally set a replacement.

    Args:
        tag_id: ID of the tag to deprecate
        request: Deprecation details (reason, replacement_tag_id)

    Returns:
        Updated tag information
    """
    # Find tag
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")

    # Validate replacement tag if provided
    if request.replacement_tag_id:
        replacement = db.query(Tag).filter(Tag.id == request.replacement_tag_id).first()
        if not replacement:
            raise HTTPException(
                status_code=400,
                detail=f"Replacement tag with id {request.replacement_tag_id} not found"
            )
        if replacement.id == tag_id:
            raise HTTPException(status_code=400, detail="Cannot replace tag with itself")

    # Update tag
    tag.is_active = False
    tag.deprecated_reason = request.deprecated_reason
    tag.replacement_tag_id = request.replacement_tag_id

    try:
        db.commit()
        db.refresh(tag)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e

    return {
        "success": True,
        "tag": {
            "id": tag.id,
            "name": tag.name,
            "is_active": tag.is_active,
            "deprecated_reason": tag.deprecated_reason,
            "replacement_tag_id": tag.replacement_tag_id
        }
    }


@router.put("/tags/{tag_id}/activate")
async def activate_tag(tag_id: int, db: Session = Depends(get_db)):
    """Reactivate a deprecated tag.

    Args:
        tag_id: ID of the tag to activate

    Returns:
        Updated tag information
    """
    # Find tag
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")

    # Update tag
    tag.is_active = True
    tag.deprecated_reason = None
    tag.replacement_tag_id = None

    try:
        db.commit()
        db.refresh(tag)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e

    return {
        "success": True,
        "tag": {
            "id": tag.id,
            "name": tag.name,
            "is_active": tag.is_active
        }
    }


# ============================================================
# Media Asset Garbage Collection (Phase 6-7)
# ============================================================

@router.get("/media-assets/orphans")
async def detect_orphan_assets(db: Session = Depends(get_db)):
    """Scan for orphaned media assets (dry-run detection only)."""
    try:
        gc = MediaGCService(db)
        report = gc.detect_orphans()
        return {"success": True, **report.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/media-assets/cleanup")
async def cleanup_orphan_assets(
    dry_run: bool = True,
    db: Session = Depends(get_db),
):
    """Clean up orphaned and expired temporary media assets.

    Args:
        dry_run: If True (default), only report what would be deleted.
    """
    try:
        gc = MediaGCService(db)
        orphan_result = gc.cleanup_orphans(dry_run=dry_run)
        temp_result = gc.cleanup_expired_temp(dry_run=dry_run)
        return {
            "success": True,
            "orphans": orphan_result.to_dict(),
            "expired_temp": temp_result.to_dict(),
            "total_deleted": orphan_result.deleted + temp_result.deleted,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


@router.get("/media-assets/stats")
async def media_asset_stats(db: Session = Depends(get_db)):
    """Get media asset statistics including orphan counts."""
    try:
        gc = MediaGCService(db)
        stats = gc.get_stats()
        return {"success": True, **stats.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}
