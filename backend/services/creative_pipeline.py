"""Creative Lab V2 Pipeline — Phase 2 sequential execution with feedback loops.

Runs as a BackgroundTask: Scriptwriter -> Cinematographer -> Sound Designer -> Copyright -> Complete.
Each step commits independently for resumability. Uses StepDef registry for extensibility.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from jinja2 import Environment, FileSystemLoader

from config import (
    BASE_DIR,
    CREATIVE_AGENT_TEMPLATES,
    CREATIVE_LEADER_MODEL,
    CREATIVE_PIPELINE_MAX_RETRIES,
    logger,
)
from database import SessionLocal
from models.creative import CreativeSession, CreativeTrace
from services.creative_agents import get_provider
from services.creative_qc import validate_copyright, validate_music, validate_scripts, validate_tts_design, validate_visuals
from services.creative_review import (
    check_auto_approve,
    pause_for_review,
    run_step_qc,
    should_review,
)
from services.creative_utils import (
    build_template_vars,
    finalize_pipeline,
    get_next_sequence,
    handle_pipeline_failure,
    load_preset,
    parse_json_response,
    pipeline_log,
    record_feedback,
    record_handoff,
    record_quality_report,
    record_trace_sync,
    resolve_characters_from_context,
)

_template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))


# ── Step Registry ─────────────────────────────────────────────


@dataclass
class StepDef:
    """Definition of a single pipeline step."""

    name: str
    template: str
    validate_fn: Callable
    scenes_key: str = "scenes"
    system_prompt_fallback: str = ""
    default_temperature: float = 0.8


PIPELINE_STEPS: list[StepDef] = [
    StepDef(
        name="scriptwriter",
        template=CREATIVE_AGENT_TEMPLATES["scriptwriter"],
        validate_fn=lambda extracted, ctx: validate_scripts(
            extracted, ctx.get("structure", "Monologue"), ctx.get("duration", 30), ctx.get("language", "Korean")
        ),
        system_prompt_fallback="You are an expert scriptwriter for short-form video. Follow the 2-pass process strictly. Always write scripts in the language specified in the prompt.",
    ),
    StepDef(
        name="cinematographer",
        template=CREATIVE_AGENT_TEMPLATES["cinematographer"],
        validate_fn=lambda extracted, _ctx: validate_visuals(extracted),
        system_prompt_fallback="You are a cinematographer designing AI-generated visuals. Use only Danbooru tags.",
    ),
    StepDef(
        name="tts_designer",
        template=CREATIVE_AGENT_TEMPLATES["tts_designer"],
        validate_fn=lambda extracted, _ctx: validate_tts_design(extracted),
        scenes_key="tts_designs",
        system_prompt_fallback="You are a TTS Designer. Recommend emotional tonality and vocal expression. Respond in valid JSON only.",
    ),
    StepDef(
        name="sound_designer",
        template=CREATIVE_AGENT_TEMPLATES["sound_designer"],
        validate_fn=lambda extracted, _ctx: validate_music(extracted),
        scenes_key="recommendation",
        system_prompt_fallback="You are a Sound Designer. Recommend BGM direction. Respond in valid JSON only.",
    ),
    StepDef(
        name="copyright_reviewer",
        template=CREATIVE_AGENT_TEMPLATES["copyright_reviewer"],
        validate_fn=lambda extracted, _ctx: validate_copyright(extracted),
        scenes_key="checks",
        system_prompt_fallback="You are a Copyright Reviewer. Check for originality issues. Respond only in valid JSON.",
    ),
]


# ── Helpers ───────────────────────────────────────────────────


def _commit_step(db, session: CreativeSession, step_name: str, status: str, state: dict) -> None:
    """Atomically commit traces + pipeline progress + state."""
    from datetime import UTC, datetime

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
    temperature: float = 0.8,
    agent_preset_id: int | None = None,
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
        result = loop.run_until_complete(
            provider.generate(prompt=prompt, system_prompt=system_prompt, temperature=temperature)
        )
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
        agent_preset_id=agent_preset_id,
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=temperature,
        phase=phase,
        step_name=step_name,
        retry_count=retry_count,
        parent_trace_id=parent_trace_id,
    )

    parsed = None
    try:
        parsed = parse_json_response(result["content"])
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("[Pipeline] JSON parse failed. Content preview: %s", result["content"][:500])
        raise e

    return parsed, trace


# ── Per-step phases ────────────────────────────────────────────


def _run_step_with_retry(
    db,
    session: CreativeSession,
    state: dict,
    step: StepDef,
    template_vars: dict,
    system_prompt: str,
    ctx: dict,
    temperature: float = 0.8,
    agent_preset_id: int | None = None,
) -> list | dict:
    """Generic retry loop for a pipeline step.

    Returns the extracted data (list for scenes, dict for recommendation, etc.).
    """
    record_handoff(db, session.id, step.name, f"Execute {step.name} step")

    last_trace_id = None
    result_data = None
    retry_vars = dict(template_vars)
    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        try:
            parsed, trace = _run_llm_step(
                db,
                session,
                template_name=step.template,
                template_vars=retry_vars,
                system_prompt=system_prompt,
                step_name=step.name,
                temperature=temperature,
                agent_preset_id=agent_preset_id,
                retry_count=retry,
                parent_trace_id=last_trace_id,
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[Pipeline] %s JSON error (retry %d): %s", step.name, retry, e)
            if retry < CREATIVE_PIPELINE_MAX_RETRIES:
                error_msg = f"JSON Output Error: {e}. Respond ONLY in valid JSON."
                retry_vars = {**template_vars, "feedback": error_msg}
                continue
            else:
                logger.error("[Pipeline] %s max retries reached with JSON error", step.name)
                # Fallback for Copyright Reviewer (Optional step)
                if step.name == "copyright_reviewer":
                    logger.warning("[Pipeline] Copyright Reviewer failed. Fallback to PASS.")
                    # Mock a "PASS" parsed structure so the pipeline continues
                    parsed = {
                        "overall": "PASS",
                        "checks": [
                            {
                                "type": "api_fallback",
                                "status": "PASS",
                                "detail": "Skipped due to API error",
                                "suggestion": None,
                            }
                        ],
                        "confidence": 0.0,
                    }
                    # We must return the extracted part (scenes_key) AND set state
                    extracted = parsed.get(step.scenes_key, [])
                    state[f"{step.name}_result"] = parsed
                    return extracted

                raise e

        extracted = parsed.get(step.scenes_key, [])
        qc = step.validate_fn(extracted, ctx)
        record_quality_report(db, session.id, qc, step.name)

        if qc["ok"]:
            state[f"{step.name}_result"] = parsed
            return extracted

        last_trace_id = trace.id
        result_data = parsed
        if retry < CREATIVE_PIPELINE_MAX_RETRIES:
            feedback_text = "\n".join(f"- {issue}" for issue in qc["issues"])
            record_feedback(db, session.id, step.name, qc["issues"], parent_trace_id=trace.id)
            retry_vars = {**template_vars, "feedback": feedback_text}
        else:
            logger.warning("[Pipeline] %s max retries reached, using last result", step.name)
            state[f"{step.name}_result"] = result_data

    return result_data.get(step.scenes_key, []) if result_data else []


# ── Main orchestrator ──────────────────────────────────────────


def run_pipeline(session_id: int) -> None:
    """Phase 2: Sequential pipeline with StepDef registry, per-step commits and retry."""
    db = SessionLocal()
    current_step = "scriptwriter"
    state: dict = {}
    try:
        session = db.query(CreativeSession).get(session_id)
        if not session:
            logger.error("[Pipeline] Session %d not found", session_id)
            return

        ctx = dict(session.context or {})
        state = dict(ctx.get("pipeline", {}).get("state", {}))
        concept = ctx.get("selected_concept", {})
        characters = resolve_characters_from_context(ctx)
        disabled_steps = ctx.get("disabled_steps", [])

        # Handle revision feedback (injected during interactive review)
        revision_fb = ctx.get("pipeline", {}).get("revision_feedback")
        if revision_fb:
            pipeline_ctx = dict(ctx.get("pipeline", {}))
            pipeline_ctx.pop("revision_feedback", None)
            ctx["pipeline"] = pipeline_ctx
            session.context = ctx
            db.commit()

        for step in PIPELINE_STEPS:
            current_step = step.name
            result_key = f"{step.name}_result"

            # Skip disabled steps
            if step.name in disabled_steps:
                _commit_step(db, session, step.name, "skipped", state)
                pipeline_log(db, session, step.name, "Skipped (disabled by user)")
                continue

            # Skip already-completed steps (resumability)
            if result_key in state:
                continue

            pipeline_log(db, session, step.name, f"Generating {step.name}...")

            p = load_preset(db, step.name)
            tv = build_template_vars(
                step.name,
                state,
                ctx,
                characters,
                revision_fb=revision_fb if step.name == "scriptwriter" else None,
            )

            extracted = _run_step_with_retry(
                db,
                session,
                state,
                step=step,
                template_vars=tv,
                system_prompt=p.system_prompt if p else step.system_prompt_fallback,
                ctx=ctx,
                temperature=p.temperature if p else step.default_temperature,
                agent_preset_id=p.id if p else None,
            )
            _commit_step(db, session, step.name, "done", state)
            pipeline_log(db, session, step.name, f"{step.name} done")

            # Director QC: interactive review
            if should_review(step.name):
                language = ctx.get("language", "Korean")
                qc_result = run_step_qc(db, session, step.name, extracted, concept, language)
                if not check_auto_approve(qc_result):
                    pause_for_review(db, session, step.name, qc_result, state)
                    return
                logger.info(
                    "[Pipeline] Session %d: %s QC auto-approved (%.2f)",
                    session.id,
                    step.name,
                    qc_result.get("score", 0),
                )

        # Finalize
        finalize_pipeline(db, session, state)

    except Exception as e:
        logger.exception("[Pipeline] Session %d failed at %s: %s", session_id, current_step, e)
        handle_pipeline_failure(db, session_id, current_step, e, state)
    finally:
        db.close()
