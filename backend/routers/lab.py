"""Lab API router -- experiments and analytics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.lab import LabExperiment
from schemas_lab import (
    LabBatchRunRequest,
    LabBatchRunResponse,
    LabExperimentListResponse,
    LabExperimentResponse,
    LabExperimentRunRequest,
    TagEffectivenessReport,
)
from services.lab import (
    aggregate_tag_effectiveness,
    run_batch,
    run_experiment,
    sync_to_engine,
)

router = APIRouter(prefix="/lab", tags=["lab"])


@router.post("/experiments/run", response_model=LabExperimentResponse)
async def api_run_experiment(
    req: LabExperimentRunRequest,
    db: Session = Depends(get_db),
):
    """Run a single tag render experiment."""
    experiment = await run_experiment(
        db=db,
        target_tags=req.target_tags,
        character_id=req.character_id,
        negative_prompt=req.negative_prompt,
        sd_params=req.sd_params,
        seed=req.seed,
        experiment_type=req.experiment_type,
        scene_description=req.scene_description,
        notes=req.notes,
    )
    return experiment


@router.post(
    "/experiments/compose-and-run",
    response_model=LabExperimentResponse,
)
async def api_compose_and_run(
    req: LabExperimentRunRequest,
    db: Session = Depends(get_db),
):
    """Scene Lab: compose scene description via V3, then generate and validate."""
    if not req.scene_description:
        raise HTTPException(
            status_code=400,
            detail="scene_description is required",
        )
    if not req.character_id:
        raise HTTPException(
            status_code=400,
            detail="character_id is required for scene translation",
        )

    from services.lab import compose_and_run

    experiment = await compose_and_run(
        db=db,
        scene_description=req.scene_description,
        character_id=req.character_id,
        negative_prompt=req.negative_prompt,
        sd_params=req.sd_params,
        seed=req.seed,
        notes=req.notes,
    )
    return experiment


@router.post("/experiments/run-batch", response_model=LabBatchRunResponse)
async def api_run_batch(
    req: LabBatchRunRequest,
    db: Session = Depends(get_db),
):
    """Run a batch of experiments."""
    result = await run_batch(
        db=db,
        target_tags=req.target_tags,
        count=req.count,
        character_id=req.character_id,
        negative_prompt=req.negative_prompt,
        sd_params=req.sd_params,
        seeds=req.seeds,
        notes=req.notes,
    )
    return result


@router.get("/experiments", response_model=LabExperimentListResponse)
def api_list_experiments(
    experiment_type: str | None = None,
    character_id: int | None = None,
    batch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List experiments with optional filters."""
    query = db.query(LabExperiment)
    if experiment_type:
        query = query.filter(LabExperiment.experiment_type == experiment_type)
    if character_id:
        query = query.filter(LabExperiment.character_id == character_id)
    if batch_id:
        query = query.filter(LabExperiment.batch_id == batch_id)

    total = query.count()
    items = (
        query.order_by(LabExperiment.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return LabExperimentListResponse(items=items, total=total)


@router.get(
    "/experiments/{experiment_id}",
    response_model=LabExperimentResponse,
)
def api_get_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    """Get a single experiment by ID."""
    experiment = (
        db.query(LabExperiment).filter_by(id=experiment_id).first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.delete("/experiments/{experiment_id}")
def api_delete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    """Delete an experiment."""
    experiment = (
        db.query(LabExperiment).filter_by(id=experiment_id).first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(experiment)
    db.commit()
    return {"ok": True}


@router.get(
    "/analytics/tag-effectiveness",
    response_model=TagEffectivenessReport,
)
def api_get_tag_effectiveness(
    db: Session = Depends(get_db),
):
    """Get aggregated tag effectiveness report."""
    report = aggregate_tag_effectiveness(db)
    return report


@router.post("/analytics/sync-effectiveness")
def api_sync_effectiveness(
    db: Session = Depends(get_db),
):
    """Sync lab effectiveness data to tag_effectiveness table."""
    count = sync_to_engine(db)
    return {"synced": count}
