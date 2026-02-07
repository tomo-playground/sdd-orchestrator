"""Creative Engine orchestration — multi-agent debate framework."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from config import CREATIVE_LEADER_MODEL, CREATIVE_MAX_ROUNDS, logger
from models.creative import (
    CreativeAgentPreset,
    CreativeSession,
    CreativeSessionRound,
    CreativeTrace,
)
from services.creative_agents import generate_parallel, get_provider
from services.creative_trace import record_trace


def _get_active_session(db: Session, session_id: int) -> CreativeSession:
    """Fetch a session with soft-delete filter."""
    session = (
        db.query(CreativeSession).filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None)).first()
    )
    if not session:
        msg = f"Session {session_id} not found"
        raise ValueError(msg)
    return session


# ── Default evaluation criteria by task_type ─────────────────

DEFAULT_CRITERIA: dict[str, dict] = {
    "scenario": None,  # lazy-loaded from creative_tasks.scenario
}


def _get_criteria(task_type: str) -> dict:
    """Get default evaluation criteria for a task_type."""
    if task_type == "scenario":
        from services.creative_tasks.scenario import DEFAULT_SCENARIO_CRITERIA

        return DEFAULT_SCENARIO_CRITERIA.copy()
    return {}


# ── Session Management ───────────────────────────────────────


async def create_session(
    db: Session,
    task_type: str,
    objective: str,
    evaluation_criteria: dict | None = None,
    character_id: int | None = None,
    context: dict | None = None,
    agent_config: list[dict] | None = None,
    max_rounds: int = CREATIVE_MAX_ROUNDS,
) -> CreativeSession:
    """Create a new creative session."""
    if evaluation_criteria is None:
        evaluation_criteria = _get_criteria(task_type)

    session = CreativeSession(
        task_type=task_type,
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

    # 1. Record instruction trace
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

    # 2. Generate from all agents in parallel
    gen_results = await generate_parallel(agents=agents, objective=instruction_prompt)

    # 3. Record generation traces
    for result in gen_results:
        await record_trace(
            db=db,
            session_id=session_id,
            round_number=round_number,
            sequence=seq,
            trace_type="generation",
            agent_role=result.get("agent_role", result.get("role", "unknown")),
            input_prompt=instruction_prompt,
            output_content=result.get("output", result.get("content", "")),
            model_id=result.get("model_id", "unknown"),
            token_usage=result.get("token_usage", {}),
            latency_ms=result.get("latency_ms", 0),
            temperature=result.get("temperature", 0.9),
            agent_preset_id=result.get("preset_id"),
        )
        seq += 1

    # 4. Leader evaluation
    leader_eval = await evaluate_round(
        session=session,
        round_number=round_number,
        gen_results=gen_results,
    )

    # 5. Record evaluation trace
    await record_trace(
        db=db,
        session_id=session_id,
        round_number=round_number,
        sequence=seq,
        trace_type="evaluation",
        agent_role="leader",
        input_prompt="Evaluate agent outputs",
        output_content=leader_eval.get("summary", ""),
        model_id=CREATIVE_LEADER_MODEL,
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.3,
    )

    # 6. Create round summary
    rnd = CreativeSessionRound(
        session_id=session_id,
        round_number=round_number,
        leader_summary=leader_eval.get("summary", ""),
        round_decision=leader_eval.get("decision", "continue"),
        best_agent_role=leader_eval.get("best_agent_role"),
        best_score=leader_eval.get("best_score"),
    )
    db.add(rnd)
    db.commit()
    db.refresh(rnd)
    return rnd


async def evaluate_round(
    session: CreativeSession,
    round_number: int,
    gen_results: list[dict],
) -> dict[str, Any]:
    """Leader agent evaluates all generation outputs.

    Returns: {"summary": str, "decision": str, "scores": dict, "best_agent_role": str, "best_score": float}
    """
    leader_provider = get_provider("gemini", CREATIVE_LEADER_MODEL)
    criteria = session.evaluation_criteria or {}

    outputs_text = "\n\n".join(
        f"[{r.get('agent_role', r.get('role', 'unknown'))}]\n{r.get('output', r.get('content', ''))}"
        for r in gen_results
    )

    eval_prompt = (
        f"Round {round_number} evaluation.\n"
        f"Objective: {session.objective}\n"
        f"Criteria: {criteria}\n\n"
        f"Outputs:\n{outputs_text}\n\n"
        "Evaluate each output. Return JSON with: summary, decision (continue/converged/terminate), "
        "scores (agent_role -> {score, feedback}), best_agent_role, best_score."
    )

    try:
        result = await leader_provider.generate(
            prompt=eval_prompt,
            system_prompt="You are a creative director evaluating agent outputs. Be critical and specific.",
            temperature=0.3,
        )
        raw = result["content"]
        # Strip markdown code fences (```json ... ``` or ``` ... ```)
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
        parsed = json.loads(cleaned)
        return parsed
    except Exception as e:
        logger.warning("[Creative] Leader evaluation failed: %s, using fallback", e)
        agents = [r.get("agent_role", r.get("role", "unknown")) for r in gen_results]
        return {
            "summary": f"Auto-evaluation (round {round_number})",
            "decision": "continue",
            "scores": {a: {"score": 0.5, "feedback": "Auto-scored"} for a in agents},
            "best_agent_role": agents[0] if agents else None,
            "best_score": 0.5,
        }


# ── Debate Loop ──────────────────────────────────────────────


async def run_debate(
    db: Session,
    session_id: int,
) -> CreativeSession:
    """Run the full debate loop until convergence or max rounds."""
    session = _get_active_session(db, session_id)

    for round_num in range(1, session.max_rounds + 1):
        rnd = await run_round(db=db, session_id=session_id, round_number=round_num)

        if rnd.round_decision in ("converged", "terminate"):
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
    """Finalize a session with the selected output."""
    session = _get_active_session(db, session_id)

    if session.final_output is not None:
        msg = f"Session {session_id} already finalized"
        raise ValueError(msg)

    session.final_output = selected_output
    session.status = "completed"
    if reason:
        session.context = {**(session.context or {}), "finalize_reason": reason}
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


def _build_instruction(
    session: CreativeSession,
    round_number: int,
    user_feedback: str | None = None,
) -> str:
    """Build the instruction prompt for a round."""
    parts = [
        f"Task: {session.task_type}",
        f"Objective: {session.objective}",
        f"Round: {round_number}/{session.max_rounds}",
    ]
    if session.context:
        parts.append(f"Context: {session.context}")
    if user_feedback:
        parts.append(f"User feedback: {user_feedback}")
    return "\n".join(parts)
