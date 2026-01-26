"""Quality measurement routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import logger
from database import SessionLocal
from services.quality import batch_validate_scenes, get_quality_alerts, get_quality_summary

router = APIRouter(prefix="/quality", tags=["quality"])


class BatchValidateRequest(BaseModel):
    """Request for batch scene validation."""

    project_name: str
    scenes: list[dict]


class QualityAlertsRequest(BaseModel):
    """Request for quality alerts."""

    project_name: str
    threshold: float = 0.7


@router.post("/batch-validate")
def batch_validate(request: BatchValidateRequest):
    """Validate all scenes in a project and save quality scores.

    Example request:
    ```json
    {
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
        result = batch_validate_scenes(request.project_name, request.scenes, db)
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


@router.get("/summary/{project_name}")
def quality_summary(project_name: str):
    """Get quality summary for a project.

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
        return get_quality_summary(project_name, db)
    except Exception as exc:
        logger.exception(f"Failed to get quality summary for {project_name}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/alerts")
def quality_alerts(request: QualityAlertsRequest):
    """Get scenes with quality below threshold.

    Example request:
    ```json
    {
        "project_name": "my_project",
        "threshold": 0.7
    }
    ```

    Returns:
    ```json
    [
        {
            "scene_id": 2,
            "match_rate": 0.45,
            "missing_tags": ["classroom", "sitting"],
            "prompt": "...",
            "image_url": "..."
        }
    ]
    ```
    """
    db = SessionLocal()
    try:
        alerts = get_quality_alerts(request.project_name, request.threshold, db)
        if alerts:
            logger.warning(
                f"{len(alerts)} scenes below {request.threshold:.0%} threshold "
                f"in project {request.project_name}"
            )
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as exc:
        logger.exception(f"Failed to get quality alerts for {request.project_name}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()
