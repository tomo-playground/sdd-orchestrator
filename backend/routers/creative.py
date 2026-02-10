"""Creative Lab API router -- shorts pipeline sessions."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.creative import CreativeSession
from schemas_creative import (
    CreativeSessionListResponse,
    CreativeSessionResponse,
    OkResponse,
    PipelineStatusResponse,
    RetrySessionRequest,
    ReviewActionRequest,
    ReviewMessageRequest,
    SelectConceptRequest,
    SendToStudioRequest,
    SendToStudioResponse,
    ShortsSessionCreate,
    StepReviewResponse,
    TraceTimelineResponse,
)
from services.creative_trace import get_session_timeline

router = APIRouter(prefix="/lab/creative", tags=["creative"])


def _get_session_or_404(db: Session, session_id: int) -> CreativeSession:
    session = (
        db.query(CreativeSession).filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None)).first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── Sessions ─────────────────────────────────────────────────


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
    return _get_session_or_404(db, session_id)


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


# ── Shorts Pipeline ─────────────────────────────────────────


@router.post("/sessions/shorts", response_model=CreativeSessionResponse, status_code=201)
async def api_create_shorts_session(
    req: ShortsSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a shorts pipeline session."""
    from services.creative_studio import create_shorts_session

    return create_shorts_session(
        db,
        topic=req.topic,
        duration=req.duration,
        structure=req.structure,
        language=req.language,
        character_id=req.character_id,
        character_ids=req.character_ids,
        references=req.references,
        max_rounds=req.max_rounds,
        director_mode=req.director_mode,
    )


@router.post("/sessions/{session_id}/run-debate", response_model=PipelineStatusResponse, status_code=202)
async def api_run_debate_v2(
    session_id: int,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run Phase 1 concept debate."""
    session = _get_session_or_404(db, session_id)

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
    if session.status not in ("phase1_done", "step_review"):
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
        progress={
            "scriptwriter": "pending",
            "cinematographer": "pending",
            "sound_designer": "pending",
            "copyright_reviewer": "pending",
        },
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
    from services.creative_studio import send_to_studio

    session = _get_session_or_404(db, session_id)
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session must be completed")

    try:
        result = send_to_studio(
            db=db,
            session=session,
            group_id=req.group_id,
            title=req.title,
            deep_parse=req.deep_parse,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return SendToStudioResponse(**result)


# ── Interactive Review ─────────────────────────────────────


@router.get("/sessions/{session_id}/review", response_model=StepReviewResponse)
def api_get_review(session_id: int, db: Session = Depends(get_db)):
    """Get current step review state."""
    session = _get_session_or_404(db, session_id)
    ctx = dict(session.context or {})
    review = ctx.get("pipeline", {}).get("review")
    if not review or session.status != "step_review":
        raise HTTPException(status_code=404, detail="No active review")
    step = review.get("step", "")
    try:
        return StepReviewResponse(
            step=step,
            result=ctx.get("pipeline", {}).get("state", {}).get(f"{step}_result"),
            qc_analysis=review.get("qc_analysis"),
            messages=review.get("messages", []),
        )
    except Exception as e:
        logger.error("[Review] Response construction failed for session %d: %s", session_id, e)
        raise HTTPException(status_code=500, detail=f"Review data format error: {e}") from e


@router.post("/sessions/{session_id}/review/message", response_model=StepReviewResponse)
async def api_review_message(
    session_id: int,
    req: ReviewMessageRequest,
    db: Session = Depends(get_db),
):
    """Send a chat message to the QC Agent during review."""
    from services.creative_review import run_script_qc_async

    session = _get_session_or_404(db, session_id)
    if session.status != "step_review":
        raise HTTPException(status_code=400, detail="Session is not in review")

    ctx = dict(session.context or {})
    pipeline = dict(ctx.get("pipeline", {}))
    review = dict(pipeline.get("review", {}))
    messages = list(review.get("messages", []))

    now_iso = datetime.now(UTC).isoformat()
    messages.append({"role": "user", "content": req.message, "timestamp": now_iso})

    # Get context for QC agent response
    step = review.get("step", "scriptwriter")
    state = pipeline.get("state", {})
    scenes = state.get(f"{step}_result", {}).get("scenes", [])
    concept = ctx.get("selected_concept", {})
    language = ctx.get("language", "Korean")

    # Re-run QC (non-blocking async)
    qc_result = await run_script_qc_async(db, session, scenes, concept, language)
    review["qc_analysis"] = qc_result

    agent_reply = qc_result.get("summary", "Analysis updated.")
    messages.append({"role": "agent", "content": agent_reply, "timestamp": datetime.now(UTC).isoformat()})

    review["messages"] = messages
    pipeline["review"] = review
    ctx["pipeline"] = pipeline
    session.context = ctx
    db.commit()

    return StepReviewResponse(
        step=step,
        result=state.get(f"{step}_result"),
        qc_analysis=qc_result,
        messages=messages,
    )


@router.post("/sessions/{session_id}/review/action", response_model=PipelineStatusResponse, status_code=202)
def api_review_action(
    session_id: int,
    req: ReviewActionRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Approve or request revision for current review step."""
    session = (
        db.query(CreativeSession)
        .filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None))
        .with_for_update()
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "step_review":
        raise HTTPException(status_code=409, detail="Session is not in review (may have been already processed)")

    ctx = dict(session.context or {})
    review = ctx.get("pipeline", {}).get("review", {})
    step = review.get("step", "scriptwriter")

    from services.creative_review import clear_review, format_revision_feedback, inject_revision_feedback

    if req.action == "approve":
        clear_review(db, session)
        session.status = "phase2_running"
        db.commit()
    else:
        qc_result = review.get("qc_analysis", {})
        feedback = format_revision_feedback(qc_result, req.feedback)
        inject_revision_feedback(db, session, step, feedback)

    from services.creative_pipeline import run_pipeline

    bg.add_task(run_pipeline, session_id=session_id)

    progress = ctx.get("pipeline", {}).get("progress")
    return PipelineStatusResponse(
        status="phase2_running",
        session_type=session.session_type or "shorts",
        progress=progress,
    )
