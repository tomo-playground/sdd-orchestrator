"""Keyword management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import CACHE_DIR, logger
from database import get_db
from models.tag import Tag
from schemas import KeywordApproveRequest
from services.keywords import (
    get_effective_tags,
    get_tag_effectiveness_report,
    load_keyword_suggestions,
    load_tags_from_db,
    normalize_prompt_token,
)

router = APIRouter(prefix="/keywords", tags=["keywords"])


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
