"""Quality measurement routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from schemas import ConsistencyResponse
from services.consistency import compute_storyboard_consistency
from services.quality import batch_validate_scenes, get_quality_alerts, get_quality_summary

service_router = APIRouter(prefix="/quality", tags=["quality"])
admin_router = APIRouter(prefix="/quality", tags=["quality-admin"])


class BatchValidateRequest(BaseModel):
    """Request for batch scene validation."""

    storyboard_id: int
    scenes: list[dict]


@admin_router.post("/batch-validate")
def batch_validate(request: BatchValidateRequest, db: Session = Depends(get_db)):
    """Validate all scenes in a project and save quality scores.

    Example request:
    ```json
    {
        "storyboard_id": 1,
        "scenes": [
            {"scene_id": 1, "image_url": "/outputs/images/scene_1.png", "prompt": "..."},
            {"scene_id": 2, "image_url": "/outputs/images/scene_2.png", "prompt": "..."}
        ]
    }
    ```

    Returns:
    ```json
    {
        "total": 10,
        "validated": 9,
        "average_match_rate": 0.82,
        "scores": [...]
    }
    ```
    """
    try:
        result = batch_validate_scenes(request.scenes, db, storyboard_id=request.storyboard_id)
        logger.info(
            f"Batch validated {result['validated']}/{result['total']} scenes (avg: {result['average_match_rate']:.1%})"
        )
        return result
    except Exception as exc:
        from services.error_responses import raise_user_error

        raise_user_error("batch_validate", exc)


@service_router.get("/summary/storyboard/{storyboard_id}")
def quality_summary_by_id(storyboard_id: int, db: Session = Depends(get_db)):
    """Get quality summary for a storyboard by ID."""
    try:
        return get_quality_summary(db, storyboard_id=storyboard_id)
    except Exception as exc:
        from services.error_responses import raise_user_error

        raise_user_error("quality_summary", exc)


@service_router.get("/summary/{storyboard_id}")
def quality_summary(storyboard_id: int, db: Session = Depends(get_db)):
    """Get quality summary for a storyboard.

    Returns:
    ```json
    {
        "total_scenes": 10,
        "average_match_rate": 0.82,
        "excellent_count": 6,
        "good_count": 2,
        "poor_count": 2,
        "scores": [...]
    }
    ```
    """
    try:
        return get_quality_summary(db, storyboard_id=storyboard_id)
    except Exception as exc:
        from services.error_responses import raise_user_error

        raise_user_error("quality_summary", exc)


@service_router.get("/consistency/{storyboard_id}", response_model=ConsistencyResponse)
def consistency(storyboard_id: int, db: Session = Depends(get_db)):
    """Cross-scene character consistency analysis for a storyboard."""
    from models.storyboard import Storyboard

    try:
        exists = db.query(Storyboard.id).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Storyboard not found")
        return compute_storyboard_consistency(storyboard_id, db)
    except HTTPException:
        raise
    except Exception as exc:
        from services.error_responses import raise_user_error

        raise_user_error("consistency_analysis", exc)


@service_router.get("/alerts/{storyboard_id}")
def quality_alerts(storyboard_id: int, threshold: float = 0.7, db: Session = Depends(get_db)):
    """Get scenes with quality below threshold for a storyboard."""
    try:
        alerts = get_quality_alerts(threshold, db, storyboard_id=storyboard_id)
        if alerts:
            logger.warning(f"{len(alerts)} scenes below {threshold:.0%} threshold in storyboard {storyboard_id}")
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as exc:
        from services.error_responses import raise_user_error

        raise_user_error("quality_alerts", exc)
