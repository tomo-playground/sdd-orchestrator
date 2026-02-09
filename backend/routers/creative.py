"""Creative Engine API router -- sessions, rounds, presets."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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
    PipelineStatusResponse,
    RetrySessionRequest,
    RunRoundRequest,
    SelectConceptRequest,
    SendToStudioRequest,
    SendToStudioResponse,
    ShortsSessionCreate,
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
        objective=req.objective,
        evaluation_criteria=req.evaluation_criteria,
        character_id=req.character_id,
        context=req.context,
        agent_config=req.agent_config,
        max_rounds=req.max_rounds,
    )


@router.get("/sessions", response_model=CreativeSessionListResponse)
def api_list_sessions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List creative sessions."""
    query = db.query(CreativeSession).filter(CreativeSession.deleted_at.is_(None))
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


# ── V2 Shorts Pipeline ──────────────────────────────────────


def _get_session_or_404(db: Session, session_id: int) -> CreativeSession:
    session = (
        db.query(CreativeSession).filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None)).first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/shorts", response_model=CreativeSessionResponse, status_code=201)
async def api_create_shorts_session(
    req: ShortsSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a V2 shorts pipeline session."""
    from services.creative_tasks import get_default_criteria

    try:
        criteria = get_default_criteria("scenario")
    except (ValueError, ModuleNotFoundError):
        criteria = {}

    session = CreativeSession(
        objective=req.topic,
        evaluation_criteria=criteria,
        character_id=req.character_id,
        context={
            "duration": req.duration,
            "structure": req.structure,
            "language": req.language,
            "references": req.references or [],
        },
        max_rounds=req.max_rounds,
        status="created",
        session_type="shorts",
        director_mode=req.director_mode,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/run-debate", response_model=PipelineStatusResponse, status_code=202)
async def api_run_debate_v2(
    session_id: int,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run Phase 1 concept debate (V2) or full debate (V1)."""
    session = _get_session_or_404(db, session_id)

    # V1 path: existing behavior
    if session.session_type == "free":
        if session.status != "running":
            raise HTTPException(status_code=400, detail="Session is not running")
        result = await run_debate(db=db, session_id=session_id)
        return PipelineStatusResponse(
            status=result.status,
            session_type="free",
        )

    # V2 path: background task
    if session.status != "created":
        raise HTTPException(status_code=400, detail=f"Cannot start debate from status '{session.status}'")

    session.status = "phase1_running"
    db.commit()

    from services.creative_shorts import run_debate_v2

    bg.add_task(run_debate_v2, session_id=session_id)
    return PipelineStatusResponse(
        status="phase1_running",
        session_type="shorts",
    )


@router.post("/sessions/{session_id}/select-concept", response_model=CreativeSessionResponse)
async def api_select_concept(
    session_id: int,
    req: SelectConceptRequest,
    db: Session = Depends(get_db),
):
    """Select a concept from Phase 1 candidates."""
    session = _get_session_or_404(db, session_id)
    if session.session_type != "shorts":
        raise HTTPException(status_code=400, detail="Not a shorts session")
    if session.status != "phase1_done":
        raise HTTPException(status_code=400, detail=f"Cannot select concept in status '{session.status}'")

    candidates = (session.concept_candidates or {}).get("candidates", [])
    if req.concept_index < 0 or req.concept_index >= len(candidates):
        raise HTTPException(status_code=400, detail=f"Invalid concept index {req.concept_index}")

    selected = candidates[req.concept_index]
    session.selected_concept_index = req.concept_index
    ctx = dict(session.context or {})
    ctx["selected_concept"] = selected.get("concept", {})
    session.context = ctx
    db.commit()
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/run-pipeline", response_model=PipelineStatusResponse, status_code=202)
async def api_run_pipeline(
    session_id: int,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run Phase 2 production pipeline (Scriptwriter → Cinematographer)."""
    session = (
        db.query(CreativeSession)
        .filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None))
        .with_for_update()
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.session_type != "shorts":
        raise HTTPException(status_code=400, detail="Not a shorts session")
    if session.status != "phase1_done":
        raise HTTPException(status_code=400, detail=f"Cannot run pipeline from status '{session.status}'")
    if session.selected_concept_index is None:
        raise HTTPException(status_code=400, detail="No concept selected. Call select-concept first.")

    session.status = "phase2_running"
    db.commit()

    from services.creative_pipeline import run_pipeline

    bg.add_task(run_pipeline, session_id=session_id)
    return PipelineStatusResponse(
        status="phase2_running",
        session_type="shorts",
        progress={"scriptwriter": "pending", "cinematographer": "pending", "copyright_reviewer": "pending"},
    )


@router.post("/sessions/{session_id}/retry", response_model=PipelineStatusResponse, status_code=202)
async def api_retry_session(
    session_id: int,
    req: RetrySessionRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Retry a failed session (resume or restart)."""
    session = _get_session_or_404(db, session_id)
    if session.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed sessions can be retried")

    ctx = dict(session.context or {})
    pipeline = ctx.get("pipeline", {})

    if req.mode == "restart":
        pipeline["state"] = {}
        pipeline["progress"] = {}
        pipeline.pop("error", None)
        pipeline.pop("failed_at", None)

    ctx["pipeline"] = pipeline
    session.context = ctx
    session.status = "phase2_running"
    db.commit()

    from services.creative_pipeline import run_pipeline

    bg.add_task(run_pipeline, session_id=session_id)
    return PipelineStatusResponse(
        status="phase2_running",
        session_type=session.session_type,
        progress=pipeline.get("progress"),
    )


@router.post("/sessions/{session_id}/send-to-studio", response_model=SendToStudioResponse)
async def api_send_to_studio(
    session_id: int,
    req: SendToStudioRequest,
    db: Session = Depends(get_db),
):
    """Send completed scenes to Studio as a new storyboard (shallow copy)."""
    from models.scene import Scene
    from models.storyboard import Storyboard

    session = _get_session_or_404(db, session_id)
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session must be completed")

    final = session.final_output or {}
    scenes_data = final.get("scenes", [])
    if not scenes_data:
        raise HTTPException(status_code=400, detail="No scenes to send")

    ctx = dict(session.context or {})
    title = req.title or f"Creative Lab: {session.objective[:50]}"
    structure = ctx.get("structure", "Monologue")

    # Create storyboard
    storyboard = Storyboard(
        group_id=req.group_id,
        title=title,
        structure=structure,
        description=session.objective,
    )
    db.add(storyboard)
    db.flush()

    # Build prompt composer for deep_parse mode
    builder = None
    if req.deep_parse:
        from services.prompt.v3_composition import V3PromptBuilder

        builder = V3PromptBuilder(db)

    # Create scenes from pipeline output
    for s in scenes_data:
        image_prompt = s.get("image_prompt", "")
        context_tags = s.get("context_tags")

        if builder and image_prompt:
            from services.creative_utils import parse_image_prompt_to_tags

            tags = parse_image_prompt_to_tags(image_prompt)
            if session.character_id:
                image_prompt = builder.compose_for_character(session.character_id, tags)
            else:
                image_prompt = builder.compose(tags)
            context_tags = {"original_tags": tags, "composed": True}

        scene = Scene(
            storyboard_id=storyboard.id,
            order=s.get("order", 0),
            script=s.get("script", ""),
            speaker=s.get("speaker", "A"),
            duration=s.get("duration", 2.5),
            image_prompt=image_prompt,
            image_prompt_ko=s.get("image_prompt_ko", ""),
            context_tags=context_tags,
        )
        db.add(scene)

    db.commit()
    return SendToStudioResponse(storyboard_id=storyboard.id, scene_count=len(scenes_data))


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
