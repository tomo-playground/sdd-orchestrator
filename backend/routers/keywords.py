"""Keyword management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from config import CACHE_DIR, logger
from schemas import KeywordApproveRequest
from services.keywords import (
    load_keyword_suggestions,
    load_keywords_file,
    normalize_prompt_token,
    reset_keyword_cache,
    save_keywords_file,
)

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.get("/suggestions")
async def list_keyword_suggestions(min_count: int = 3, limit: int = 50):
    logger.info("📥 [Keyword Suggestions] min_count=%s limit=%s", min_count, limit)
    suggestions = load_keyword_suggestions(min_count=min_count, limit=limit)
    return {"min_count": min_count, "limit": limit, "suggestions": suggestions}


@router.get("/categories")
async def list_keyword_categories():
    logger.info("📥 [Keyword Categories]")
    try:
        data = load_keywords_file()
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        return {"categories": categories}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Keyword categories load failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/approve")
async def approve_keyword(request: KeywordApproveRequest):
    logger.info("📥 [Keyword Approve] %s", request.model_dump())
    tag_token = normalize_prompt_token(request.tag)
    if not tag_token:
        raise HTTPException(status_code=400, detail="Invalid tag")
    category = request.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category is required")
    try:
        data = load_keywords_file()
        categories = data.get("categories", {})
        if not isinstance(categories, dict):
            categories = {}
        if category not in categories:
            raise HTTPException(status_code=400, detail="Unknown category")
        entries = categories.get(category) or []
        if not isinstance(entries, list):
            entries = []
        existing = {normalize_prompt_token(item) for item in entries}
        if tag_token not in existing:
            entries.append(tag_token)
        categories[category] = entries
        data["categories"] = categories
        save_keywords_file(data)
        reset_keyword_cache()
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
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Keyword approval failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
