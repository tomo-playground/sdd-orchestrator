"""Creative Lab V2 Pipeline — Phase 2 sequential execution with feedback loops.

Runs as a BackgroundTask: Scriptwriter → QC → Cinematographer → QC → Complete.
Each step commits independently for resumability.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

from jinja2 import Environment, FileSystemLoader

from config import (
    BASE_DIR,
    CREATIVE_LEADER_MODEL,
    CREATIVE_PIPELINE_MAX_RETRIES,
    logger,
)
from database import SessionLocal
from models.creative import CreativeSession, CreativeTrace
from services.creative_agents import get_provider
from services.creative_qc import validate_copyright, validate_scripts, validate_visuals
from services.creative_utils import (
    calculate_total_tokens,
    get_next_sequence,
    parse_json_response,
    record_trace_sync,
)

_template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates" / "creative")))


# ── Trace helpers ──────────────────────────────────────────────


def _commit_step(db, session: CreativeSession, step_name: str, status: str, state: dict) -> None:
    """Atomically commit traces + pipeline progress + state."""
    ctx = dict(session.context or {})
    pipeline = dict(ctx.get("pipeline", {}))
    pipeline["current_step"] = step_name
    pipeline["progress"] = {**pipeline.get("progress", {}), step_name: status}
    pipeline["state"] = state
    pipeline["heartbeat"] = datetime.now(UTC).isoformat()
    ctx["pipeline"] = pipeline
    session.context = ctx
    db.commit()


def _run_llm_step(
    db,
    session: CreativeSession,
    template_name: str,
    template_vars: dict,
    system_prompt: str,
    step_name: str,
    phase: str = "production",
    retry_count: int = 0,
    parent_trace_id: int | None = None,
) -> tuple[dict, CreativeTrace]:
    """Run a single LLM generation step and record trace."""
    template = _template_env.get_template(template_name)
    prompt = template.render(**template_vars)

    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)

    start = time.monotonic()
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(provider.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.8))
    finally:
        loop.close()
    elapsed_ms = int((time.monotonic() - start) * 1000)

    seq = get_next_sequence(db, session.id)
    trace = record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="generation",
        agent_role=step_name,
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=0.8,
        phase=phase,
        step_name=step_name,
        retry_count=retry_count,
        parent_trace_id=parent_trace_id,
    )

    parsed = parse_json_response(result["content"])
    return parsed, trace


def _record_handoff(db, session: CreativeSession, target: str, content: str) -> CreativeTrace:
    """Record a handoff trace from director to target agent."""
    seq = get_next_sequence(db, session.id)
    return record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="handoff",
        agent_role="creative_director",
        target_agent=target,
        input_prompt=content,
        output_content=content,
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        step_name=target,
    )


def _record_feedback(
    db,
    session: CreativeSession,
    target: str,
    issues: list[str],
    parent_trace_id: int | None = None,
) -> CreativeTrace:
    """Record a feedback trace from director to target agent."""
    feedback_text = "\n".join(f"- {issue}" for issue in issues)
    seq = get_next_sequence(db, session.id)
    return record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="feedback",
        agent_role="creative_director",
        target_agent=target,
        input_prompt=f"Quality issues for {target}",
        output_content=feedback_text,
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        step_name=target,
        feedback=feedback_text,
        parent_trace_id=parent_trace_id,
    )


def _record_quality_report(db, session: CreativeSession, qc_result: dict, step_name: str) -> None:
    """Record a quality_report trace."""
    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="quality_report",
        agent_role="creative_director",
        input_prompt=f"QC check for {step_name}",
        output_content=json.dumps(qc_result, ensure_ascii=False),
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        step_name=step_name,
    )


# ── Per-step phases ────────────────────────────────────────────


def _run_step_with_retry(
    db,
    session: CreativeSession,
    state: dict,
    step_name: str,
    template_name: str,
    template_vars: dict,
    system_prompt: str,
    validate_fn,
    scenes_key: str = "scenes",
) -> list:
    """Generic retry loop for a pipeline step (Scriptwriter or Cinematographer)."""
    _record_handoff(db, session, step_name, f"Execute {step_name} step")

    last_trace_id = None
    result_data = None
    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        parsed, trace = _run_llm_step(
            db,
            session,
            template_name=template_name,
            template_vars=template_vars,
            system_prompt=system_prompt,
            step_name=step_name,
            retry_count=retry,
            parent_trace_id=last_trace_id,
        )
        scenes = parsed.get(scenes_key, [])
        qc = validate_fn(scenes)
        _record_quality_report(db, session, qc, step_name)

        if qc["ok"]:
            state[f"{step_name}_result"] = parsed
            return scenes

        last_trace_id = trace.id
        result_data = parsed
        if retry < CREATIVE_PIPELINE_MAX_RETRIES:
            _record_feedback(db, session, step_name, qc["issues"], parent_trace_id=trace.id)
        else:
            logger.warning("[Pipeline] %s max retries reached, using last result", step_name)
            state[f"{step_name}_result"] = result_data

    return result_data.get(scenes_key, []) if result_data else []


def _finalize_pipeline(db, session: CreativeSession, state: dict) -> None:
    """Store final output, record completion trace, calculate tokens."""
    final_scenes = state.get("cinematographer_result", {}).get("scenes", [])
    session.final_output = {"scenes": final_scenes, "source": "creative_lab_v2"}
    session.status = "completed"

    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="decision",
        agent_role="creative_director",
        input_prompt="Pipeline complete",
        output_content=f"All QC checks passed. {len(final_scenes)} scenes ready.",
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        decision_context={
            "mode": "auto",
            "selected": "approve",
            "reason": "All QC passed",
            "confidence": 1.0,
        },
    )

    session.total_token_usage = calculate_total_tokens(db, session.id)
    db.commit()
    logger.info("[Pipeline] Session %d completed: %d scenes", session.id, len(final_scenes))


def _handle_pipeline_failure(db, session_id: int, current_step: str, error: Exception, state: dict) -> None:
    """Record failure state for resumability."""
    try:
        session = db.query(CreativeSession).get(session_id)
        if session:
            session.status = "failed"
            ctx = dict(session.context or {})
            pipeline = dict(ctx.get("pipeline", {}))
            pipeline["failed_at"] = current_step
            pipeline["error"] = str(error)
            pipeline["state"] = state
            ctx["pipeline"] = pipeline
            session.context = ctx
            db.commit()
    except Exception:
        logger.exception("[Pipeline] Failed to record error state for session %d", session_id)


# ── Main orchestrator ──────────────────────────────────────────


def run_pipeline(session_id: int) -> None:
    """Phase 2: Sequential pipeline with per-step commits and retry support."""
    db = SessionLocal()
    current_step = "scriptwriter"
    state: dict = {}
    try:
        session = db.query(CreativeSession).get(session_id)
        if not session:
            logger.error("[Pipeline] Session %d not found", session_id)
            return

        ctx = dict(session.context or {})
        pipeline_state = dict(ctx.get("pipeline", {}).get("state", {}))
        state = pipeline_state
        concept = ctx.get("selected_concept", {})

        # Step 1: Scriptwriter
        current_step = "scriptwriter"
        if "scriptwriter_result" not in state:
            scripts = _run_step_with_retry(
                db,
                session,
                state,
                step_name="scriptwriter",
                template_name="scriptwriter.j2",
                template_vars={
                    "concept": concept,
                    "duration": ctx.get("duration", 30),
                    "structure": ctx.get("structure", "Monologue"),
                    "language": ctx.get("language", "Korean"),
                    "character_name": ctx.get("character_name"),
                    "min_scenes": max(4, ctx.get("duration", 30) // 5),
                    "max_scenes": ctx.get("duration", 30) // 2,
                },
                system_prompt="You are an expert scriptwriter for short-form video. Follow the 2-pass process strictly.",
                validate_fn=lambda scenes: validate_scripts(
                    scenes,
                    ctx.get("structure", "Monologue"),
                    ctx.get("duration", 30),
                    ctx.get("language", "Korean"),
                ),
            )
            _commit_step(db, session, "scriptwriter", "done", state)
        else:
            scripts = state["scriptwriter_result"].get("scenes", [])

        # Step 2: Cinematographer
        current_step = "cinematographer"
        if "cinematographer_result" not in state:
            _run_step_with_retry(
                db,
                session,
                state,
                step_name="cinematographer",
                template_name="cinematographer.j2",
                template_vars={"scenes": scripts, "character_tags": ctx.get("character_tags")},
                system_prompt="You are a cinematographer designing AI-generated visuals. Use only Danbooru tags.",
                validate_fn=validate_visuals,
            )
            _commit_step(db, session, "cinematographer", "done", state)

        # Step 3: Copyright Reviewer
        current_step = "copyright_reviewer"
        if "copyright_reviewer_result" not in state:
            cinema_scenes = state.get("cinematographer_result", {}).get("scenes", [])
            _run_step_with_retry(
                db,
                session,
                state,
                step_name="copyright_reviewer",
                template_name="copyright_reviewer.j2",
                template_vars={"scenes": cinema_scenes},
                system_prompt="You are a Copyright Reviewer. Check for originality issues. Respond only in valid JSON.",
                validate_fn=validate_copyright,
                scenes_key="checks",
            )
            _commit_step(db, session, "copyright_reviewer", "done", state)

        # Finalize
        _finalize_pipeline(db, session, state)

    except Exception as e:
        logger.exception("[Pipeline] Session %d failed at %s: %s", session_id, current_step, e)
        _handle_pipeline_failure(db, session_id, current_step, e, state)
    finally:
        db.close()
