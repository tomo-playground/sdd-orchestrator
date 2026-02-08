"""Creative Engine API router -- sessions, rounds, presets."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.creative import CreativeAgentPreset, CreativeSession
from schemas_creative import (
    AgentPresetCreate,
    AgentPresetResponse,
    AgentPresetUpdate,
    CreativeSessionCreate,
    CreativeSessionListResponse,
    CreativeSessionResponse,
    FinalizeRequest,
    OkResponse,
    RunRoundRequest,
    TaskTypeListResponse,
    TraceTimelineResponse,
)
from services.creative_engine import create_session, finalize, run_debate, run_round
from services.creative_trace import get_session_timeline

router = APIRouter(prefix="/lab/creative", tags=["creative"])


# ── Sessions ─────────────────────────────────────────────────


@router.post("/sessions", response_model=CreativeSessionResponse)
async def api_create_session(
    req: CreativeSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new creative session."""
    return await create_session(
        db=db,
        task_type=req.task_type,
        objective=req.objective,
        evaluation_criteria=req.evaluation_criteria,
        character_id=req.character_id,
        context=req.context,
        agent_config=req.agent_config,
        max_rounds=req.max_rounds,
    )


@router.get("/sessions", response_model=CreativeSessionListResponse)
def api_list_sessions(
    task_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List creative sessions with optional task_type filter."""
    query = db.query(CreativeSession).filter(CreativeSession.deleted_at.is_(None))
    if task_type:
        query = query.filter(CreativeSession.task_type == task_type)
    total = query.count()
    items = query.order_by(CreativeSession.id.desc()).offset(offset).limit(limit).all()
    return CreativeSessionListResponse(items=items, total=total)


@router.get("/sessions/{session_id}", response_model=CreativeSessionResponse)
def api_get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a creative session by ID."""
    session = (
        db.query(CreativeSession).filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None)).first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/run-round", response_model=CreativeSessionResponse)
async def api_run_round(
    session_id: int,
    req: RunRoundRequest | None = None,
    db: Session = Depends(get_db),
):
    """Run a single round for a session."""
    session = db.get(CreativeSession, session_id)
    if not session or session.deleted_at:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")

    round_count = len(session.rounds)
    await run_round(
        db=db,
        session_id=session_id,
        round_number=round_count + 1,
        user_feedback=req.feedback if req else None,
    )
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/run-debate", response_model=CreativeSessionResponse)
async def api_run_debate(
    session_id: int,
    db: Session = Depends(get_db),
):
    """Run the full debate loop for a session."""
    session = db.get(CreativeSession, session_id)
    if not session or session.deleted_at:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")
    return await run_debate(db=db, session_id=session_id)


@router.post("/sessions/{session_id}/finalize", response_model=CreativeSessionResponse)
async def api_finalize(
    session_id: int,
    req: FinalizeRequest,
    db: Session = Depends(get_db),
):
    """Finalize a session with the selected output."""
    try:
        return await finalize(
            db=db,
            session_id=session_id,
            selected_output=req.selected_output,
            reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}/timeline", response_model=TraceTimelineResponse)
async def api_get_timeline(
    session_id: int,
    db: Session = Depends(get_db),
):
    """Get the full trace timeline for a session."""
    timeline = await get_session_timeline(db=db, session_id=session_id)
    if not timeline.get("session"):
        raise HTTPException(status_code=404, detail="Session not found")
    return timeline


@router.delete("/sessions/{session_id}", response_model=OkResponse)
def api_delete_session(session_id: int, db: Session = Depends(get_db)):
    """Soft-delete a creative session."""
    session = db.get(CreativeSession, session_id)
    if not session or session.deleted_at:
        raise HTTPException(status_code=404, detail="Session not found")
    session.deleted_at = datetime.now(UTC)
    db.commit()
    return {"ok": True}


# ── Task Types ───────────────────────────────────────────────


@router.get("/task-types", response_model=TaskTypeListResponse)
def api_list_task_types():
    """List all available creative task types."""
    from services.creative_tasks import TASK_REGISTRY

    items = [{"key": k, **v} for k, v in TASK_REGISTRY.items()]
    return TaskTypeListResponse(items=items)


# ── Agent Presets ────────────────────────────────────────────


@router.get("/agent-presets", response_model=list[AgentPresetResponse])
def api_list_presets(db: Session = Depends(get_db)):
    """List all active agent presets."""
    return (
        db.query(CreativeAgentPreset)
        .filter(CreativeAgentPreset.deleted_at.is_(None))
        .order_by(CreativeAgentPreset.id)
        .all()
    )


@router.post("/agent-presets", response_model=AgentPresetResponse)
def api_create_preset(
    req: AgentPresetCreate,
    db: Session = Depends(get_db),
):
    """Create a new agent preset."""
    preset = CreativeAgentPreset(**req.model_dump())
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.put("/agent-presets/{preset_id}", response_model=AgentPresetResponse)
def api_update_preset(
    preset_id: int,
    req: AgentPresetUpdate,
    db: Session = Depends(get_db),
):
    """Update an agent preset."""
    preset = db.get(CreativeAgentPreset, preset_id)
    if not preset or preset.deleted_at:
        raise HTTPException(status_code=404, detail="Preset not found")
    if preset.is_system:
        raise HTTPException(status_code=400, detail="Cannot edit system presets")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(preset, field, value)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/agent-presets/{preset_id}", response_model=OkResponse)
def api_delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete an agent preset."""
    preset = db.get(CreativeAgentPreset, preset_id)
    if not preset or preset.deleted_at:
        raise HTTPException(status_code=404, detail="Preset not found")
    if preset.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system presets")

    preset.deleted_at = datetime.now(UTC)
    db.commit()
    return {"ok": True}
