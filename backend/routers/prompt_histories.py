"""Prompt History CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models import PromptHistory
from schemas import (
    PromptHistoryApplyResponse,
    PromptHistoryCreate,
    PromptHistoryResponse,
    PromptHistoryUpdate,
)

router = APIRouter(prefix="/prompt-histories", tags=["prompt-histories"])


@router.get("", response_model=list[PromptHistoryResponse])
async def list_prompt_histories(
    favorite: bool | None = Query(None, description="Filter by favorite status"),
    character_id: int | None = Query(None, description="Filter by character ID"),
    search: str | None = Query(None, description="Search in name and prompt"),
    sort: str = Query("created_at", description="Sort by: created_at, use_count, avg_match_rate"),
    db: Session = Depends(get_db),
):
    """List prompt histories with optional filters."""
    query = db.query(PromptHistory)

    if favorite is not None:
        query = query.filter(PromptHistory.is_favorite == favorite)

    if character_id is not None:
        query = query.filter(PromptHistory.character_id == character_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (PromptHistory.name.ilike(search_pattern))
            | (PromptHistory.positive_prompt.ilike(search_pattern))
        )

    if sort == "use_count":
        query = query.order_by(desc(PromptHistory.use_count))
    elif sort == "avg_match_rate":
        query = query.order_by(desc(PromptHistory.avg_match_rate))
    else:
        query = query.order_by(desc(PromptHistory.created_at))

    histories = query.all()
    logger.info("[PromptHistory] Listed %d items", len(histories))
    return histories


@router.get("/{history_id}", response_model=PromptHistoryResponse)
async def get_prompt_history(history_id: int, db: Session = Depends(get_db)):
    """Get a single prompt history by ID."""
    history = db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Prompt history not found")
    return history


@router.post("", response_model=PromptHistoryResponse, status_code=201)
async def create_prompt_history(data: PromptHistoryCreate, db: Session = Depends(get_db)):
    """Create a new prompt history."""
    history_data = data.model_dump()
    if history_data.get("lora_settings"):
        history_data["lora_settings"] = [
            {
                "lora_id": ls.get("lora_id", 0),
                "name": ls.get("name", "unknown"),
                "weight": ls.get("weight", 0.7),
                "trigger_words": ls.get("trigger_words", []),
            }
            for ls in history_data["lora_settings"]
        ]

    history = PromptHistory(**history_data)
    db.add(history)
    db.commit()
    db.refresh(history)
    logger.info("[PromptHistory] Created: %s (id=%d)", history.name, history.id)
    return history


@router.put("/{history_id}", response_model=PromptHistoryResponse)
async def update_prompt_history(
    history_id: int, data: PromptHistoryUpdate, db: Session = Depends(get_db)
):
    """Update an existing prompt history."""
    history = db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Prompt history not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(history, key, value)

    db.commit()
    db.refresh(history)
    logger.info("[PromptHistory] Updated: %s (id=%d)", history.name, history.id)
    return history


@router.delete("/{history_id}")
async def delete_prompt_history(history_id: int, db: Session = Depends(get_db)):
    """Delete a prompt history."""
    history = db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Prompt history not found")

    name = history.name
    db.delete(history)
    db.commit()
    logger.info("[PromptHistory] Deleted: %s (id=%d)", name, history_id)
    return {"ok": True, "deleted": name}


@router.post("/{history_id}/toggle-favorite", response_model=PromptHistoryResponse)
async def toggle_favorite(history_id: int, db: Session = Depends(get_db)):
    """Toggle favorite status."""
    history = db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Prompt history not found")

    history.is_favorite = not history.is_favorite
    db.commit()
    db.refresh(history)
    logger.info(
        "[PromptHistory] Toggled favorite: %s -> %s", history.name, history.is_favorite
    )
    return history


@router.post("/{history_id}/apply", response_model=PromptHistoryApplyResponse)
async def apply_prompt_history(history_id: int, db: Session = Depends(get_db)):
    """Apply a prompt history (increments use_count)."""
    history = db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Prompt history not found")

    history.use_count += 1
    db.commit()
    db.refresh(history)
    logger.info("[PromptHistory] Applied: %s (use_count=%d)", history.name, history.use_count)

    return PromptHistoryApplyResponse(
        id=history.id,
        positive_prompt=history.positive_prompt,
        negative_prompt=history.negative_prompt,
        steps=history.steps,
        cfg_scale=history.cfg_scale,
        sampler_name=history.sampler_name,
        seed=history.seed,
        clip_skip=history.clip_skip,
        lora_settings=history.lora_settings,
        context_tags=history.context_tags,
        use_count=history.use_count,
    )


@router.post("/{history_id}/update-score", response_model=PromptHistoryResponse)
async def update_score(
    history_id: int,
    match_rate: float = Query(..., ge=0, le=100, description="WD14 match rate"),
    db: Session = Depends(get_db),
):
    """Update WD14 validation score."""
    history = db.query(PromptHistory).filter(PromptHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Prompt history not found")

    history.last_match_rate = match_rate
    history.validation_count += 1

    # Calculate running average
    if history.avg_match_rate is None:
        history.avg_match_rate = match_rate
    else:
        n = history.validation_count
        history.avg_match_rate = ((history.avg_match_rate * (n - 1)) + match_rate) / n

    db.commit()
    db.refresh(history)
    logger.info(
        "[PromptHistory] Score updated: %s (rate=%.1f%%, avg=%.1f%%)",
        history.name,
        match_rate,
        history.avg_match_rate,
    )
    return history
