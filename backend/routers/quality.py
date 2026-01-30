"""Quality measurement routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import logger
from database import SessionLocal
from services.quality import batch_validate_scenes, get_quality_alerts, get_quality_summary

router = APIRouter(prefix="/quality", tags=["quality"])


class BatchValidateRequest(BaseModel):
    """Request for batch scene validation."""

    storyboard_id: int
    scenes: list[dict]



@router.post("/batch-validate")
def batch_validate(request: BatchValidateRequest):
    """Validate all scenes in a project and save quality scores.

    Example request:
    ```json
    {
        "storyboard_id": 1,
        "project_name": "my_project",
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
    db = SessionLocal()
    try:
        # Pass storyboard_id
        result = batch_validate_scenes(
            request.scenes, 
            db, 
            storyboard_id=request.storyboard_id
        )
        logger.info(
            f"Batch validated {result['validated']}/{result['total']} scenes "
            f"(avg: {result['average_match_rate']:.1%})"
        )
        return result
    except Exception as exc:
        logger.exception("Batch validation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/summary/storyboard/{storyboard_id}")
def quality_summary_by_id(storyboard_id: int):
    """Get quality summary for a storyboard by ID."""
    db = SessionLocal()
    try:
        return get_quality_summary(None, db, storyboard_id=storyboard_id)
    except Exception as exc:
        logger.exception(f"Failed to get quality summary for storyboard {storyboard_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/summary/{storyboard_id}")
def quality_summary(storyboard_id: int):
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
    db = SessionLocal()
    try:
        return get_quality_summary(db, storyboard_id=storyboard_id)
    except Exception as exc:
        logger.exception(f"Failed to get quality summary for storyboard {storyboard_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/alerts/{storyboard_id}")
def quality_alerts(storyboard_id: int, threshold: float = 0.7):
    """Get scenes with quality below threshold for a storyboard."""
    db = SessionLocal()
    try:
        alerts = get_quality_alerts(threshold, db, storyboard_id=storyboard_id)
        if alerts:
            logger.warning(
                f"{len(alerts)} scenes below {threshold:.0%} threshold "
                f"in storyboard {storyboard_id}"
            )
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as exc:
        logger.exception(f"Failed to get quality alerts for storyboard {storyboard_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()
