"""Trace recording and querying for Creative Engine sessions."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.creative import CreativeSession, CreativeSessionRound, CreativeTrace


async def record_trace(
    db: Session,
    session_id: int,
    round_number: int,
    sequence: int,
    trace_type: str,
    agent_role: str,
    input_prompt: str,
    output_content: str,
    model_id: str,
    token_usage: dict[str, int],
    latency_ms: int,
    temperature: float,
    agent_preset_id: int | None = None,
    score: float | None = None,
    feedback: str | None = None,
    parent_trace_id: int | None = None,
    diff_summary: str | None = None,
) -> CreativeTrace:
    """Record a single LLM interaction trace."""
    trace = CreativeTrace(
        session_id=session_id,
        round_number=round_number,
        sequence=sequence,
        trace_type=trace_type,
        agent_role=agent_role,
        agent_preset_id=agent_preset_id,
        input_prompt=input_prompt,
        output_content=output_content,
        score=score,
        feedback=feedback,
        model_id=model_id,
        token_usage=token_usage,
        latency_ms=latency_ms,
        temperature=temperature,
        parent_trace_id=parent_trace_id,
        diff_summary=diff_summary,
    )
    db.add(trace)
    db.flush()
    return trace


def _serialize_trace(trace: CreativeTrace) -> dict[str, Any]:
    """Serialize a trace ORM object to dict."""
    return {
        "id": trace.id,
        "session_id": trace.session_id,
        "round_number": trace.round_number,
        "sequence": trace.sequence,
        "trace_type": trace.trace_type,
        "agent_role": trace.agent_role,
        "agent_preset_id": trace.agent_preset_id,
        "input_prompt": trace.input_prompt,
        "output_content": trace.output_content,
        "score": trace.score,
        "feedback": trace.feedback,
        "model_id": trace.model_id,
        "token_usage": trace.token_usage,
        "latency_ms": trace.latency_ms,
        "temperature": trace.temperature,
        "parent_trace_id": trace.parent_trace_id,
        "diff_summary": trace.diff_summary,
        "created_at": trace.created_at,
    }


def _serialize_round(rnd: CreativeSessionRound) -> dict[str, Any]:
    """Serialize a round ORM object to dict."""
    return {
        "id": rnd.id,
        "session_id": rnd.session_id,
        "round_number": rnd.round_number,
        "leader_summary": rnd.leader_summary,
        "round_decision": rnd.round_decision,
        "best_agent_role": rnd.best_agent_role,
        "best_score": rnd.best_score,
        "created_at": rnd.created_at,
    }


def _serialize_session(session: CreativeSession) -> dict[str, Any]:
    """Serialize a session ORM object to dict."""
    return {
        "id": session.id,
        "task_type": session.task_type,
        "objective": session.objective,
        "evaluation_criteria": session.evaluation_criteria,
        "character_id": session.character_id,
        "context": session.context,
        "agent_config": session.agent_config,
        "final_output": session.final_output,
        "max_rounds": session.max_rounds,
        "total_token_usage": session.total_token_usage,
        "status": session.status,
    }


async def get_session_timeline(db: Session, session_id: int) -> dict[str, Any]:
    """Return full session timeline with rounds and traces as serialized dicts."""
    session = (
        db.query(CreativeSession)
        .filter(CreativeSession.id == session_id, CreativeSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        return {"session": None, "rounds": [], "traces": []}

    rounds = (
        db.query(CreativeSessionRound)
        .filter(CreativeSessionRound.session_id == session_id)
        .order_by(CreativeSessionRound.round_number)
        .all()
    )

    traces = (
        db.query(CreativeTrace)
        .filter(CreativeTrace.session_id == session_id)
        .order_by(CreativeTrace.round_number, CreativeTrace.sequence)
        .all()
    )

    return {
        "session": _serialize_session(session),
        "rounds": [_serialize_round(r) for r in rounds],
        "traces": [_serialize_trace(t) for t in traces],
    }


async def get_agent_comparison(
    db: Session,
    session_id: int,
) -> list[dict[str, Any]]:
    """Compare agent performance across all rounds in a session."""
    traces = (
        db.query(CreativeTrace)
        .filter(
            CreativeTrace.session_id == session_id,
            CreativeTrace.trace_type == "generation",
        )
        .all()
    )

    agent_stats: dict[str, dict[str, Any]] = {}
    for t in traces:
        role = t.agent_role
        if role not in agent_stats:
            agent_stats[role] = {
                "agent_role": role,
                "generations": 0,
                "avg_latency_ms": 0,
                "total_tokens": 0,
                "scores": [],
            }
        stats = agent_stats[role]
        stats["generations"] += 1
        stats["total_tokens"] += (t.token_usage or {}).get("total_tokens", 0)
        stats["avg_latency_ms"] += t.latency_ms

    eval_traces = (
        db.query(CreativeTrace)
        .filter(
            CreativeTrace.session_id == session_id,
            CreativeTrace.trace_type == "evaluation",
        )
        .all()
    )
    for et in eval_traces:
        role = et.agent_role
        if role in agent_stats and et.score is not None:
            agent_stats[role]["scores"].append(et.score)

    results = []
    for stats in agent_stats.values():
        count = stats["generations"]
        stats["avg_latency_ms"] = stats["avg_latency_ms"] // count if count else 0
        scores = stats.pop("scores")
        stats["avg_score"] = sum(scores) / len(scores) if scores else None
        results.append(stats)

    return sorted(results, key=lambda x: x.get("avg_score") or 0, reverse=True)
