"""Generation log routes for analytics and pattern learning."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import logger
from database import SessionLocal
from models.generation_log import GenerationLog

router = APIRouter(prefix="/generation-logs", tags=["generation-logs"])


class CreateGenerationLogRequest(BaseModel):
    """Request for creating a generation log."""

    project_name: str
    scene_index: int
    prompt: str | None = None
    tags: list[str] | None = None
    sd_params: dict | None = None
    match_rate: float | None = None
    seed: int | None = None
    status: str | None = "pending"  # success, fail, pending
    image_url: str | None = None


class UpdateStatusRequest(BaseModel):
    """Request for updating generation log status."""

    status: str  # success, fail, pending


@router.post("")
def create_generation_log(request: CreateGenerationLogRequest):
    """Create a new generation log entry.

    Example request:
    ```json
    {
        "project_name": "my_project",
        "scene_index": 0,
        "prompt": "1girl, smiling, classroom, ...",
        "tags": ["1girl", "smiling", "classroom"],
        "sd_params": {"steps": 20, "cfg_scale": 7, "seed": 12345},
        "match_rate": 0.85,
        "seed": 12345,
        "status": "success",
        "image_url": "/outputs/images/scene_0.png"
    }
    ```

    Returns:
    ```json
    {
        "id": 1,
        "project_name": "my_project",
        "scene_index": 0,
        ...
    }
    ```
    """
    db = SessionLocal()
    try:
        log = GenerationLog(
            project_name=request.project_name,
            scene_index=request.scene_index,
            prompt=request.prompt,
            tags=request.tags,
            sd_params=request.sd_params,
            match_rate=request.match_rate,
            seed=request.seed,
            status=request.status,
            image_url=request.image_url,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(
            f"Created generation log: project={request.project_name}, "
            f"scene={request.scene_index}, status={request.status}"
        )

        return {
            "id": log.id,
            "project_name": log.project_name,
            "scene_index": log.scene_index,
            "status": log.status,
            "match_rate": log.match_rate,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create generation log")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/project/{project_name}")
def get_project_logs(project_name: str, status: str | None = None, limit: int = 100):
    """Get generation logs for a project.

    Query parameters:
    - status: Filter by status (success, fail, pending)
    - limit: Max number of results (default: 100)

    Returns:
    ```json
    {
        "logs": [
            {
                "id": 1,
                "scene_index": 0,
                "match_rate": 0.85,
                "status": "success",
                ...
            }
        ],
        "total": 10
    }
    ```
    """
    db = SessionLocal()
    try:
        query = db.query(GenerationLog).filter(GenerationLog.project_name == project_name)

        if status:
            query = query.filter(GenerationLog.status == status)

        logs = query.order_by(GenerationLog.created_at.desc()).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "scene_index": log.scene_index,
                    "prompt": log.prompt,
                    "tags": log.tags,
                    "sd_params": log.sd_params,
                    "match_rate": log.match_rate,
                    "seed": log.seed,
                    "status": log.status,
                    "image_url": log.image_url,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "total": len(logs),
        }
    except Exception as exc:
        logger.exception(f"Failed to get logs for project {project_name}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.patch("/{log_id}/status")
def update_log_status(log_id: int, request: UpdateStatusRequest):
    """Update the status of a generation log.

    Example request:
    ```json
    {
        "status": "success"
    }
    ```

    Returns updated log.
    """
    db = SessionLocal()
    try:
        log = db.query(GenerationLog).filter(GenerationLog.id == log_id).first()

        if not log:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        log.status = request.status
        db.commit()
        db.refresh(log)

        logger.info(f"Updated generation log {log_id} status to {request.status}")

        return {
            "id": log.id,
            "status": log.status,
            "match_rate": log.match_rate,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(f"Failed to update log {log_id} status")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.delete("/{log_id}")
def delete_log(log_id: int):
    """Delete a generation log."""
    db = SessionLocal()
    try:
        log = db.query(GenerationLog).filter(GenerationLog.id == log_id).first()

        if not log:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        db.delete(log)
        db.commit()

        logger.info(f"Deleted generation log {log_id}")

        return {"message": f"Log {log_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(f"Failed to delete log {log_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()
