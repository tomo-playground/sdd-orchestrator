"""Keyword management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import CACHE_DIR, logger
from database import get_db
from models.tag import Tag
from schemas import BatchApproveRequest, KeywordApproveRequest
from services.keywords import (
    CATEGORY_PATTERNS,
    CATEGORY_PRIORITY,
    get_effective_tags,
    get_tag_effectiveness_report,
    get_tag_rules_summary,
    load_keyword_suggestions,
    load_tags_from_db,
    normalize_prompt_token,
    sync_category_patterns_to_tags,
    sync_lora_triggers_to_tags,
    validate_prompt_tags,
)

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.get("/priority")
async def get_keyword_priority():
    """Get keyword category priorities and patterns for sorting."""
    logger.info("[Keyword Priority]")
    return {
        "priority": CATEGORY_PRIORITY,
        "patterns": CATEGORY_PATTERNS,
    }


@router.get("/suggestions")
async def list_keyword_suggestions(min_count: int = 3, limit: int = 50):
    logger.info("[Keyword Suggestions] min_count=%s limit=%s", min_count, limit)
    suggestions = load_keyword_suggestions(min_count=min_count, limit=limit)
    return {"min_count": min_count, "limit": limit, "suggestions": suggestions}


@router.get("/categories")
async def list_keyword_categories():
    """List keyword categories from database."""
    logger.info("[Keyword Categories]")
    try:
        grouped = load_tags_from_db()
        return {"categories": grouped}
    except Exception as exc:
        logger.exception("Keyword categories load failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/approve")
async def approve_keyword(request: KeywordApproveRequest, db: Session = Depends(get_db)):
    """Approve a keyword suggestion by adding it to the database."""
    logger.info("[Keyword Approve] %s", request.model_dump())
    tag_token = normalize_prompt_token(request.tag)
    if not tag_token:
        raise HTTPException(status_code=400, detail="Invalid tag")
    category = request.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category is required")

    try:
        # Check if tag already exists
        existing = db.query(Tag).filter(Tag.name == tag_token).first()
        if existing:
            return {"ok": True, "tag": tag_token, "category": category, "message": "Tag already exists"}

        # Add new tag to database
        new_tag = Tag(
            name=tag_token,
            category="scene",  # Default category for approved suggestions
            group_name=category,
        )
        db.add(new_tag)
        db.commit()

        # Remove from suggestions cache
        suggestions_path = CACHE_DIR / "keyword_suggestions.json"
        if suggestions_path.exists():
            try:
                suggestions = json.loads(suggestions_path.read_text(encoding="utf-8"))
                if tag_token in suggestions:
                    suggestions.pop(tag_token, None)
                    suggestions_path.write_text(json.dumps(suggestions, ensure_ascii=False, indent=2))
            except Exception:
                logger.exception("Failed to update keyword suggestions after approval")

        return {"ok": True, "tag": tag_token, "category": category}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Keyword approval failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/effectiveness")
async def get_effectiveness_report():
    """Get tag effectiveness report from WD14 feedback loop data."""
    logger.info("[Tag Effectiveness Report]")
    try:
        report = get_tag_effectiveness_report()
        summary = get_effective_tags()
        return {
            "summary": {
                "high_effectiveness": len(summary.get("high", [])),
                "medium_effectiveness": len(summary.get("medium", [])),
                "low_effectiveness": len(summary.get("low", [])),
                "unknown": len(summary.get("unknown", [])),
            },
            "tags": report,
        }
    except Exception as exc:
        logger.exception("Tag effectiveness report failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/effectiveness/summary")
async def get_effectiveness_summary():
    """Get summarized tag effectiveness grouped by level."""
    logger.info("[Tag Effectiveness Summary]")
    try:
        result = get_effective_tags()
        return result
    except Exception as exc:
        logger.exception("Tag effectiveness summary failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/batch-approve/preview")
async def batch_approve_preview(min_confidence: float = 0.7, limit: int = 200):
    """Preview tags ready for batch approval.

    Returns tags grouped by:
    - ready: confidence >= min_confidence and not skip
    - skip: suggested_category == 'skip'
    - manual: confidence < min_confidence (need manual review)
    """
    logger.info("[Batch Approve Preview] min_confidence=%s", min_confidence)
    suggestions = load_keyword_suggestions(min_count=1, limit=limit)

    ready = []
    skip = []
    manual = []

    for item in suggestions:
        cat = item.get("suggested_category", "")
        conf = item.get("confidence", 0)

        if cat == "skip":
            skip.append(item)
        elif conf >= min_confidence and cat:
            ready.append(item)
        else:
            manual.append(item)

    # Group ready tags by category
    by_category: dict[str, list] = {}
    for item in ready:
        cat = item["suggested_category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    return {
        "ready_count": len(ready),
        "skip_count": len(skip),
        "manual_count": len(manual),
        "ready_by_category": by_category,
        "skip": skip,
        "manual": manual[:20],  # Show first 20 for review
    }


@router.post("/batch-approve")
async def batch_approve(
    request: BatchApproveRequest,
    db: Session = Depends(get_db),
):
    """Batch approve tags with suggested categories.

    If tags is provided, only approve those specific tags.
    Otherwise, approve all tags with confidence >= min_confidence.
    """
    tags = request.tags
    min_confidence = request.min_confidence
    logger.info("[Batch Approve] tags=%s min_confidence=%s", tags, min_confidence)

    suggestions = load_keyword_suggestions(min_count=1, limit=500)
    suggestions_map = {item["tag"]: item for item in suggestions}

    # Determine which tags to approve
    if tags:
        to_approve = [suggestions_map[t] for t in tags if t in suggestions_map]
    else:
        to_approve = [
            item for item in suggestions
            if item.get("confidence", 0) >= min_confidence
            and item.get("suggested_category", "") not in ("", "skip")
        ]

    approved = []
    skipped = []
    failed = []

    # Map suggested_category to DB category
    category_map = {
        "expression": "scene",
        "gaze": "scene",
        "pose": "scene",
        "action": "scene",
        "camera": "scene",
        "environment": "scene",
        "mood": "scene",
        "clothing": "character",
        "hair_style": "character",
        "hair_color": "character",
        "eye_color": "character",
        "skin_color": "character",
        "appearance": "character",
    }

    for item in to_approve:
        tag = item["tag"]
        suggested_cat = item.get("suggested_category", "")

        if suggested_cat == "skip" or not suggested_cat:
            skipped.append({"tag": tag, "reason": "skip or no category"})
            continue

        tag_token = normalize_prompt_token(tag)
        if not tag_token:
            failed.append({"tag": tag, "reason": "invalid token"})
            continue

        # Check if already exists
        existing = db.query(Tag).filter(Tag.name == tag_token).first()
        if existing:
            skipped.append({"tag": tag, "reason": "already exists"})
            continue

        try:
            db_category = category_map.get(suggested_cat, "scene")
            new_tag = Tag(
                name=tag_token,
                category=db_category,
                group_name=suggested_cat,
            )
            db.add(new_tag)
            approved.append({
                "tag": tag_token,
                "category": db_category,
                "group_name": suggested_cat,
            })
        except Exception as e:
            failed.append({"tag": tag, "reason": str(e)})

    # Commit all approved tags
    if approved:
        try:
            db.commit()

            # Remove approved tags from suggestions cache
            suggestions_path = CACHE_DIR / "keyword_suggestions.json"
            if suggestions_path.exists():
                try:
                    cache_data = json.loads(suggestions_path.read_text(encoding="utf-8"))
                    for item in approved:
                        cache_data.pop(item["tag"], None)
                    suggestions_path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2))
                except Exception:
                    logger.exception("Failed to update suggestions cache after batch approve")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Commit failed: {e}") from e

    logger.info(
        "[Batch Approve Complete] approved=%d skipped=%d failed=%d",
        len(approved), len(skipped), len(failed)
    )

    return {
        "ok": True,
        "approved_count": len(approved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "approved": approved,
        "skipped": skipped,
        "failed": failed,
    }


@router.get("/rules")
async def get_tag_rules():
    """Get summary of tag conflict and requires rules."""
    logger.info("[Tag Rules Summary]")
    try:
        summary = get_tag_rules_summary()
        return summary
    except Exception as exc:
        logger.exception("Tag rules summary failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/validate")
async def validate_tags(tags: list[str]):
    """Validate a list of tags for conflicts and missing dependencies.

    Example:
        POST /keywords/validate
        ["short hair", "long hair", "twintails"]

    Returns conflicts and missing dependencies.
    """
    logger.info("[Tag Validation] tags=%s", tags[:10])
    try:
        result = validate_prompt_tags(tags)
        return result
    except Exception as exc:
        logger.exception("Tag validation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sync-lora-triggers")
async def sync_lora_triggers():
    """Sync LoRA trigger words to tags table.

    Reads all trigger words from loras table and ensures they exist
    in the tags table with appropriate categories (identity, style, etc.).

    Call this after adding/updating LoRAs to keep triggers in sync.
    """
    logger.info("[Sync LoRA Triggers]")
    try:
        result = sync_lora_triggers_to_tags()
        logger.info(
            "[Sync LoRA Triggers Complete] added=%d updated=%d skipped=%d",
            result["summary"]["added_count"],
            result["summary"]["updated_count"],
            result["summary"]["skipped_count"],
        )
        return result
    except Exception as exc:
        logger.exception("Sync LoRA triggers failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sync-category-patterns")
async def sync_category_patterns(update_existing: bool = False):
    """Sync CATEGORY_PATTERNS to tags table.

    Reads all patterns from CATEGORY_PATTERNS and ensures they exist
    in the tags table. This fills gaps between defined patterns and DB.

    Args:
        update_existing: If True, also update category/priority of existing tags.

    Returns:
        Summary of added/updated/skipped tags grouped by category.
    """
    logger.info("[Sync Category Patterns] update_existing=%s", update_existing)
    try:
        result = sync_category_patterns_to_tags(update_existing=update_existing)
        logger.info(
            "[Sync Category Patterns Complete] added=%d updated=%d skipped=%d",
            result["summary"]["added_count"],
            result["summary"]["updated_count"],
            result["summary"]["skipped_count"],
        )
        return result
    except Exception as exc:
        logger.exception("Sync category patterns failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
