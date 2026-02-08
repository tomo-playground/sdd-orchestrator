"""Creative Engine orchestration — multi-agent debate framework."""

from __future__ import annotations

import asyncio
import json

from sqlalchemy.orm import Session

from config import (
    CREATIVE_LEADER_MODEL,
    CREATIVE_MAX_ROUNDS,
    CREATIVE_URL_MAX_FETCH_COUNT,
    logger,
)
from models.creative import (
    CreativeAgentPreset,
    CreativeSession,
    CreativeSessionRound,
    CreativeTrace,
)
from services.creative_agents import generate_parallel
from services.creative_leader import (
    build_agent_feedback_context,
    evaluate_round,
    synthesize_output,
)
from services.creative_trace import (
    get_best_output,
    get_prev_evaluation,
    get_round_gen_results,
    record_trace,
    write_agent_scores,
)
from services.creative_url import extract_urls, fetch_url_content


def _get_active_session(db: Session, session_id: int) -> CreativeSession:
    """Fetch a session with soft-delete filter."""
    session = (
        db.query(CreativeSession).filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None)).first()
    )
    if not session:
        msg = f"Session {session_id} not found"
        raise ValueError(msg)
    return session


# ── Default evaluation criteria ─────────────────────────────


def _get_criteria() -> dict:
    """Get default evaluation criteria for scenario tasks."""
    from services.creative_tasks import get_default_criteria

    try:
        return get_default_criteria("scenario")
    except (ValueError, ModuleNotFoundError):
        logger.warning("[Creative] No criteria available, using empty")
        return {}


# ── Session Management ───────────────────────────────────────


async def create_session(
    db: Session,
    objective: str,
    evaluation_criteria: dict | None = None,
    character_id: int | None = None,
    context: dict | None = None,
    agent_config: list[dict] | None = None,
    max_rounds: int = CREATIVE_MAX_ROUNDS,
) -> CreativeSession:
    """Create a new creative session."""
    if evaluation_criteria is None:
        evaluation_criteria = _get_criteria()

    if not agent_config:
        system_presets = (
            db.query(CreativeAgentPreset)
            .filter(
                CreativeAgentPreset.is_system.is_(True),
                CreativeAgentPreset.deleted_at.is_(None),
                CreativeAgentPreset.name != "Leader",
            )
            .all()
        )
        if system_presets:
            agent_config = [{"preset_id": p.id, "role": p.name} for p in system_presets]
        else:
            logger.warning("[Creative] No system presets available for auto-assignment")

    # Fetch URL content from objective for agent context
    urls = extract_urls(objective)
    if urls:
        targets = urls[:CREATIVE_URL_MAX_FETCH_COUNT]
        results = await asyncio.gather(*(fetch_url_content(u) for u in targets))
        fetched = {u: r for u, r in zip(targets, results, strict=True) if r}
        if fetched:
            context = context or {}
            context["url_content"] = fetched

    session = CreativeSession(
        objective=objective,
        evaluation_criteria=evaluation_criteria,
        character_id=character_id,
        context=context,
        agent_config=agent_config,
        max_rounds=max_rounds,
        status="running",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ── Round Execution ──────────────────────────────────────────


async def run_round(
    db: Session,
    session_id: int,
    round_number: int,
    user_feedback: str | None = None,
) -> CreativeSessionRound:
    """Execute a single debate round: generate → evaluate → summarize."""
    session = _get_active_session(db, session_id)

    agents = _build_agent_list(db, session)
    seq = 0

    # 0. Get previous round evaluation for leader context
    prev_evaluation = get_prev_evaluation(db, session_id, round_number)

    # 1. Inject per-agent feedback from previous evaluation
    if prev_evaluation:
        feedback_map = build_agent_feedback_context(prev_evaluation)
        for agent in agents:
            role = agent["role"]
            if role in feedback_map:
                agent["objective"] = feedback_map[role]

    # 2. Record instruction trace
    instruction_prompt = _build_instruction(session, round_number, user_feedback)
    await record_trace(
        db=db,
        session_id=session_id,
        round_number=round_number,
        sequence=seq,
        trace_type="instruction",
        agent_role="leader",
        input_prompt=instruction_prompt,
        output_content=instruction_prompt,
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
    )
    seq += 1

    # 3. Generate from all agents in parallel
    gen_results = await generate_parallel(agents=agents, objective=instruction_prompt)

    # 4. Record generation traces
    for result in gen_results:
        await record_trace(
            db=db,
            session_id=session_id,
            round_number=round_number,
            sequence=seq,
            trace_type="generation",
            agent_role=result.get("agent_role", "unknown"),
            input_prompt=instruction_prompt,
            output_content=result.get("content", ""),
            model_id=result.get("model_id", "unknown"),
            token_usage=result.get("token_usage", {}),
            latency_ms=result.get("latency_ms", 0),
            temperature=result.get("temperature", 0.9),
            agent_preset_id=result.get("preset_id"),
        )
        seq += 1

    # 5. Leader evaluation (with previous evaluation context)
    leader_eval = await evaluate_round(
        session=session,
        round_number=round_number,
        gen_results=gen_results,
        prev_evaluation=prev_evaluation,
    )

    # 6. Record evaluation trace (full JSON for downstream use)
    eval_json = json.dumps(leader_eval, ensure_ascii=False)
    await record_trace(
        db=db,
        session_id=session_id,
        round_number=round_number,
        sequence=seq,
        trace_type="evaluation",
        agent_role="leader",
        input_prompt="Evaluate agent outputs",
        output_content=eval_json,
        model_id=CREATIVE_LEADER_MODEL,
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.3,
    )
    seq += 1

    # 7. Write per-agent scores/feedback to generation traces
    write_agent_scores(db, session_id, round_number, leader_eval)

    # 8. Create round summary
    rnd = CreativeSessionRound(
        session_id=session_id,
        round_number=round_number,
        leader_summary=leader_eval.get("summary", ""),
        round_decision=leader_eval.get("decision", "continue"),
        best_agent_role=leader_eval.get("best_agent_role"),
        best_score=leader_eval.get("best_score"),
        leader_direction=leader_eval.get("direction"),
    )
    db.add(rnd)
    db.commit()
    db.refresh(rnd)
    return rnd


# ── Debate Loop ──────────────────────────────────────────────


async def run_debate(
    db: Session,
    session_id: int,
) -> CreativeSession:
    """Run the full debate loop until convergence or max rounds."""
    session = _get_active_session(db, session_id)

    last_round: CreativeSessionRound | None = None
    last_gen_results: list[dict] = []
    last_eval: dict = {}

    for round_num in range(1, session.max_rounds + 1):
        rnd = await run_round(db=db, session_id=session_id, round_number=round_num)
        last_round = rnd

        # Retrieve eval + gen_results for potential synthesis
        last_eval = get_prev_evaluation(db, session_id, round_num + 1) or {}
        if rnd.round_decision in ("converged", "terminate"):
            last_gen_results = get_round_gen_results(db, session_id, round_num)
            break

    # Calculate total token usage from all traces
    traces = db.query(CreativeTrace).filter(CreativeTrace.session_id == session_id).all()
    total_prompt = sum((t.token_usage or {}).get("prompt_tokens", 0) for t in traces)
    total_completion = sum((t.token_usage or {}).get("completion_tokens", 0) for t in traces)

    session.total_token_usage = {
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
    }
    session.status = "completed"

    # Synthesize on convergence, otherwise use best agent output
    final_output = None
    if last_round and last_round.round_decision == "converged" and last_gen_results:
        synthesized = await synthesize_output(
            session=session,
            gen_results=last_gen_results,
            evaluation=last_eval,
        )
        if synthesized:
            final_output = synthesized

    if not final_output and last_round:
        final_output = get_best_output(db, session_id, last_round)

    if final_output:
        session.final_output = final_output
        session.context = {**(session.context or {}), "auto_finalized": True}

    db.commit()
    db.refresh(session)
    return session


# ── Finalize ─────────────────────────────────────────────────


async def finalize(
    db: Session,
    session_id: int,
    selected_output: dict,
    reason: str | None = None,
) -> CreativeSession:
    """Finalize (or re-finalize) a session with the selected output."""
    session = _get_active_session(db, session_id)

    session.final_output = selected_output
    session.status = "completed"
    ctx = dict(session.context or {})
    if reason:
        ctx["finalize_reason"] = reason
    ctx["auto_finalized"] = False
    session.context = ctx
    db.commit()
    db.refresh(session)
    return session


# ── Helpers ──────────────────────────────────────────────────


def _build_agent_list(db: Session, session: CreativeSession) -> list[dict]:
    """Convert session's agent_config to the format generate_parallel expects."""
    agents = []
    for cfg in session.agent_config or []:
        preset_id = cfg.get("preset_id")
        preset = db.get(CreativeAgentPreset, preset_id) if preset_id else None
        if preset_id and not preset:
            logger.warning("[Creative] Preset %d not found, using defaults", preset_id)

        agents.append(
            {
                "role": cfg.get("role", "unknown"),
                "preset_id": preset_id,
                "provider": preset.model_provider if preset else "gemini",
                "model_name": preset.model_name if preset else CREATIVE_LEADER_MODEL,
                "system_prompt": preset.system_prompt if preset else "You are a creative agent.",
                "temperature": preset.temperature if preset else 0.9,
            }
        )
    return agents


_CONTEXT_INTERNAL_KEYS = {"url_content", "auto_finalized", "finalize_reason"}


def _build_instruction(
    session: CreativeSession,
    round_number: int,
    user_feedback: str | None = None,
) -> str:
    """Build the instruction prompt for a round."""
    parts = [
        f"Objective: {session.objective}",
        f"Round: {round_number}/{session.max_rounds}",
    ]
    if session.context:
        url_content = session.context.get("url_content")
        if url_content:
            for url, text in url_content.items():
                parts.append(f'<reference url="{url}">\n{text}\n</reference>')
        rest = {k: v for k, v in session.context.items() if k not in _CONTEXT_INTERNAL_KEYS}
        if rest:
            parts.append(f"Context: {rest}")
    if user_feedback:
        parts.append(f"User feedback: {user_feedback}")
    return "\n".join(parts)
