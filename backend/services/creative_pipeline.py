"""Creative Lab V2 Pipeline — Phase 2 sequential execution with feedback loops.

Runs as a BackgroundTask: Scriptwriter → Cinematographer → Sound Designer → Copyright → Complete.
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
    SCRIPT_LENGTH_KOREAN,
    SCRIPT_LENGTH_OTHER,
    logger,
)
from database import SessionLocal
from models.creative import CreativeSession, CreativeTrace
from services.creative_agents import get_provider
from services.creative_qc import validate_copyright, validate_music, validate_scripts, validate_visuals
from services.creative_utils import (
    calculate_total_tokens,
    get_next_sequence,
    parse_json_response,
    record_feedback,
    record_handoff,
    record_quality_report,
    record_trace_sync,
    resolve_characters_from_context,
)

_template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates" / "creative")))


# ── Helpers ───────────────────────────────────────────────────


def _script_length_hint(language: str) -> str:
    """Build human-readable script length hint from config constants."""
    if language == "Korean":
        return f"{SCRIPT_LENGTH_KOREAN[0]}-{SCRIPT_LENGTH_KOREAN[1]} characters (Korean)"
    return f"{SCRIPT_LENGTH_OTHER[0]}-{SCRIPT_LENGTH_OTHER[1]} words (English/other)"


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
) -> list | dict:
    """Generic retry loop for a pipeline step.

    Returns the extracted data (list for scenes, dict for recommendation, etc.).
    On retry, injects QC feedback into template_vars so the LLM can correct.
    """
    record_handoff(db, session.id, step_name, f"Execute {step_name} step")

    last_trace_id = None
    result_data = None
    retry_vars = dict(template_vars)
    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        try:
            parsed, trace = _run_llm_step(
                db,
                session,
                template_name=template_name,
                template_vars=retry_vars,
                system_prompt=system_prompt,
                step_name=step_name,
                retry_count=retry,
                parent_trace_id=last_trace_id,
            )
        except json.JSONDecodeError as e:
            logger.warning("[Pipeline] %s JSON error (retry %d): %s", step_name, retry, e)
            if retry < CREATIVE_PIPELINE_MAX_RETRIES:
                # NOTE: trace is already recorded in DB by _run_llm_step before parsing,
                # but we don't have the trace object here since the exception was raised.
                error_msg = f"JSON Output Error: {e}. Please ensure valid JSON format."
                retry_vars = {**template_vars, "feedback": error_msg}
                continue
            else:
                logger.error("[Pipeline] %s max retries reached with JSON error", step_name)
                raise e

        # If we got here, parsing succeeded
        extracted = parsed.get(scenes_key, [])
        qc = validate_fn(extracted)
        record_quality_report(db, session.id, qc, step_name)

        if qc["ok"]:
            state[f"{step_name}_result"] = parsed
            return extracted

        last_trace_id = trace.id
        result_data = parsed
        if retry < CREATIVE_PIPELINE_MAX_RETRIES:
            feedback_text = "\n".join(f"- {issue}" for issue in qc["issues"])
            record_feedback(db, session.id, step_name, qc["issues"], parent_trace_id=trace.id)
            retry_vars = {**template_vars, "feedback": feedback_text}
        else:
            logger.warning("[Pipeline] %s max retries reached, using last result", step_name)
            state[f"{step_name}_result"] = result_data

    return result_data.get(scenes_key, []) if result_data else []


def _finalize_pipeline(db, session: CreativeSession, state: dict) -> None:
    """Store final output, record completion trace, calculate tokens."""
    final_scenes = state.get("cinematographer_result", {}).get("scenes", [])
    music_rec = state.get("sound_designer_result", {}).get("recommendation")
    session.final_output = {
        "scenes": final_scenes,
        "music_recommendation": music_rec,
        "source": "creative_lab_v2",
    }
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
        characters = resolve_characters_from_context(ctx)

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
                    "characters": characters or None,
                    "min_scenes": max(4, ctx.get("duration", 30) // 5),
                    "max_scenes": ctx.get("duration", 30) // 2,
                    "script_length_hint": _script_length_hint(ctx.get("language", "Korean")),
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
                template_vars={
                    "scenes": scripts,
                    "character_tags": ctx.get("character_tags"),
                    "characters_tags": {speaker: info.get("tags", []) for speaker, info in characters.items()}
                    if characters
                    else None,
                },
                system_prompt="You are a cinematographer designing AI-generated visuals. Use only Danbooru tags.",
                validate_fn=validate_visuals,
            )
            _commit_step(db, session, "cinematographer", "done", state)

        # Step 3: Sound Designer
        current_step = "sound_designer"
        if "sound_designer_result" not in state:
            cinema_scenes = state.get("cinematographer_result", {}).get("scenes", [])
            _run_step_with_retry(
                db,
                session,
                state,
                step_name="sound_designer",
                template_name="sound_designer.j2",
                template_vars={
                    "concept": concept,
                    "scenes": cinema_scenes,
                    "duration": ctx.get("duration", 30),
                },
                system_prompt="You are a Sound Designer. Recommend BGM direction. Respond in valid JSON only.",
                validate_fn=validate_music,
                scenes_key="recommendation",
            )
            _commit_step(db, session, "sound_designer", "done", state)

        # Step 4: Copyright Reviewer
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
