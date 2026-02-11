"""Creative Lab — Interactive Step Review (Pause-Review-Resume).

Handles Step QC analysis, pause/resume state transitions,
and review message processing. Separated from creative_pipeline.py
to keep the pipeline under the 400-line guideline.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from config import (
    BASE_DIR,
    CREATIVE_AUTO_APPROVE_THRESHOLD,
    CREATIVE_LEADER_MODEL,
    CREATIVE_REVIEW_ENABLED,
    CREATIVE_REVIEW_STEPS,
    logger,
)
from models.creative import CreativeSession
from services.creative_agents import get_provider
from services.creative_utils import get_next_sequence, parse_json_response, record_trace_sync

_template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))


def should_review(step_name: str) -> bool:
    """Check if a step should trigger interactive review."""
    return CREATIVE_REVIEW_ENABLED and step_name in CREATIVE_REVIEW_STEPS


def _build_step_qc_prompt(step_name: str, step_result, concept: dict, language: str) -> str:
    """Build the QC analysis prompt from the generalized template."""
    template = _template_env.get_template("creative/director_step_qc.j2")
    return template.render(step_name=step_name, step_result=step_result, concept=concept, language=language)


def _record_step_qc_trace(
    db: Session, session: CreativeSession, prompt: str, result: dict, elapsed_ms: int, step_name: str
) -> None:
    """Record a QC evaluation trace."""
    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="evaluation",
        agent_role=f"{step_name}_qc",
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=0.3,
        phase="production",
        step_name=f"{step_name}_qc",
    )


def run_step_qc(
    db: Session,
    session: CreativeSession,
    step_name: str,
    step_result,
    concept: dict,
    language: str,
) -> dict:
    """Run Director QC for any pipeline step (sync)."""
    import asyncio

    prompt = _build_step_qc_prompt(step_name, step_result, concept, language)
    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)

    start = time.monotonic()
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            provider.generate(
                prompt=prompt,
                system_prompt="You are a strict quality reviewer. Respond only in valid JSON.",
                temperature=0.3,
            )
        )
    finally:
        loop.close()
    elapsed_ms = int((time.monotonic() - start) * 1000)

    _record_step_qc_trace(db, session, prompt, result, elapsed_ms, step_name)
    return parse_json_response(result["content"])


def run_script_qc(
    db: Session,
    session: CreativeSession,
    scenes: list,
    concept: dict,
    language: str,
) -> dict:
    """Backward-compatible wrapper: Run Script QC Agent (sync)."""
    return run_step_qc(db, session, "scriptwriter", scenes, concept, language)


async def run_step_qc_async(
    db: Session,
    session: CreativeSession,
    step_name: str,
    step_result,
    concept: dict,
    language: str,
) -> dict:
    """Run Director QC for any pipeline step (async)."""
    prompt = _build_step_qc_prompt(step_name, step_result, concept, language)
    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)

    start = time.monotonic()
    result = await provider.generate(
        prompt=prompt,
        system_prompt="You are a strict quality reviewer. Respond only in valid JSON.",
        temperature=0.3,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    _record_step_qc_trace(db, session, prompt, result, elapsed_ms, step_name)
    return parse_json_response(result["content"])


async def run_script_qc_async(
    db: Session,
    session: CreativeSession,
    scenes: list,
    concept: dict,
    language: str,
) -> dict:
    """Backward-compatible async wrapper: Run Script QC Agent."""
    return await run_step_qc_async(db, session, "scriptwriter", scenes, concept, language)


def check_auto_approve(qc_result: dict) -> bool:
    """Check if QC result meets auto-approve criteria."""
    score = qc_result.get("score", 0)
    issues = qc_result.get("issues", [])
    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    return score >= CREATIVE_AUTO_APPROVE_THRESHOLD and critical_count == 0


def pause_for_review(
    db: Session,
    session: CreativeSession,
    step_name: str,
    qc_result: dict,
    state: dict,
) -> None:
    """Transition session to step_review status."""
    ctx = dict(session.context or {})
    pipeline = dict(ctx.get("pipeline", {}))

    now_iso = datetime.now(UTC).isoformat()
    pipeline["review"] = {
        "step": step_name,
        "qc_analysis": qc_result,
        "messages": [
            {
                "role": "system",
                "content": f"{step_name} QC complete. Rating: {qc_result.get('overall_rating', 'unknown')} "
                f"(score: {qc_result.get('score', 0):.2f}). "
                f"Review the results and approve or request revision.",
                "timestamp": now_iso,
            }
        ],
        "started_at": now_iso,
    }
    pipeline["state"] = state
    ctx["pipeline"] = pipeline
    session.context = ctx
    session.status = "step_review"
    db.commit()
    logger.info("[Review] Session %d paused for %s review", session.id, step_name)


def clear_review(db: Session, session: CreativeSession) -> None:
    """Remove review data from context after approval.

    NOTE: Does NOT commit — caller is responsible for committing
    together with the status change to avoid race conditions.
    """
    ctx = dict(session.context or {})
    pipeline = dict(ctx.get("pipeline", {}))
    pipeline.pop("review", None)
    ctx["pipeline"] = pipeline
    session.context = ctx


def inject_revision_feedback(
    db: Session,
    session: CreativeSession,
    step_name: str,
    feedback: str,
) -> None:
    """Inject feedback and clear step result so pipeline re-runs the step."""
    ctx = dict(session.context or {})
    pipeline = dict(ctx.get("pipeline", {}))
    state = dict(pipeline.get("state", {}))

    state.pop(f"{step_name}_result", None)
    progress = dict(pipeline.get("progress", {}))
    progress[step_name] = "pending"
    pipeline["progress"] = progress
    pipeline["state"] = state
    pipeline["revision_feedback"] = feedback
    pipeline.pop("review", None)
    ctx["pipeline"] = pipeline
    session.context = ctx
    session.status = "phase2_running"
    db.commit()
    logger.info("[Review] Session %d revision requested for %s", session.id, step_name)


def format_revision_feedback(qc_result: dict, user_feedback: str | None) -> str:
    """Merge structured QC issues with user free-text feedback."""
    parts: list[str] = []

    issues = qc_result.get("issues", [])
    if issues:
        parts.append("## QC Issues Found")
        for issue in issues:
            severity = issue.get("severity", "warning").upper()
            scene = issue.get("scene", "?")
            desc = issue.get("description", "")
            parts.append(f"- [{severity}] Scene {scene}: {desc}")

    suggestions = qc_result.get("revision_suggestions", [])
    if suggestions:
        parts.append("\n## Revision Suggestions")
        for s in suggestions:
            parts.append(f"- {s}")

    if user_feedback:
        parts.append(f"\n## User Feedback\n{user_feedback}")

    return "\n".join(parts)
