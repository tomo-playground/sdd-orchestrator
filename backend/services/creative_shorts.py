"""Creative Lab V2 — Shorts multi-agent debate orchestrator (Phase 1).

Coordinates multi-round concept debate and builds candidates for user selection.
Agent runners are in creative_debate_agents.py.
"""

from __future__ import annotations

import asyncio
import json

from config import CREATIVE_DIRECTOR_SCORE_GAP_THRESHOLD, logger
from database import SessionLocal
from models.creative import CreativeSession
from services.creative_debate_agents import (
    DebateContext,
    run_architects,
    run_devils_advocate,
    run_director_evaluate,
    run_reference_analyst,
)
from services.creative_utils import (
    calculate_total_tokens,
    get_next_sequence,
    parse_json_response,
    record_trace_sync,
)

# ── Round + candidate helpers ──────────────────────────────────


def _execute_debate_round(
    loop,
    db,
    session: CreativeSession,
    round_num: int,
    ctx: DebateContext,
) -> tuple[list[dict], dict | None, dict]:
    """Execute a single debate round: Architects -> Devil's Advocate -> Director."""
    gen_results = loop.run_until_complete(run_architects(db, session, round_num, ctx))
    db.commit()

    concepts_this_round = []
    for r in gen_results:
        try:
            parsed = parse_json_response(r.get("content", "{}"))
        except (json.JSONDecodeError, KeyError):
            parsed = {"title": "Parse error", "hook": "", "arc": ""}
        concepts_this_round.append(
            {
                "agent_role": r.get("agent_role", "unknown"),
                "content": r.get("content", ""),
                "parsed": parsed,
            }
        )

    critic_result = loop.run_until_complete(run_devils_advocate(db, session, round_num, concepts_this_round, ctx))
    db.commit()

    # Inject critic analysis into ctx for director
    old_eval = ctx.prev_evaluation_str
    critic_str = json.dumps(critic_result, ensure_ascii=False) if critic_result else None
    ctx.prev_evaluation_str = critic_str

    eval_result = loop.run_until_complete(run_director_evaluate(db, session, round_num, concepts_this_round, ctx))
    ctx.prev_evaluation_str = old_eval  # restore for next round
    db.commit()

    return concepts_this_round, critic_result, eval_result


def _check_convergence(eval_result: dict) -> bool:
    """Return True if early convergence criteria are met."""
    best_score = eval_result.get("best_score", 0)
    scores = eval_result.get("scores", {})
    sorted_scores = sorted(scores.values(), key=lambda x: x.get("score", 0), reverse=True)
    gap = (sorted_scores[0]["score"] - sorted_scores[1]["score"]) if len(sorted_scores) >= 2 else 1.0
    return best_score > 0.85 and gap > 0.2


def _prepare_next_round(
    ctx: DebateContext, concepts: list[dict], eval_result: dict, critic_result: dict | None
) -> None:
    """Update DebateContext with feedback for the next round."""
    ctx.prev_concepts = {c["agent_role"]: c["parsed"] for c in concepts}
    ctx.prev_evaluation_str = json.dumps(eval_result, ensure_ascii=False)
    ctx.director_feedback = eval_result.get("direction", "")
    if critic_result:
        ctx.critic_feedback = {"by_role": {}}
        for critique in critic_result.get("critiques", []):
            role = critique.get("agent_role", "")
            weaknesses = critique.get("weaknesses", [])
            ctx.critic_feedback["by_role"][role] = json.dumps(weaknesses, ensure_ascii=False)


def _build_concept_candidates(ctx: DebateContext) -> list[dict]:
    """Build sorted candidate list from the last round's evaluation."""
    final_round = ctx.all_round_concepts[-1] if ctx.all_round_concepts else {}
    candidates = []
    for c in final_round.get("concepts", []):
        role = c["agent_role"]
        score_data = ctx.last_eval.get("scores", {}).get(role, {})
        candidates.append(
            {
                "agent_role": role,
                "concept": c["parsed"],
                "score": score_data.get("score", 0),
                "feedback": score_data.get("feedback", ""),
                "breakdown": score_data.get("breakdown"),
            }
        )
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    return candidates


def _record_debate_decision(
    db,
    session: CreativeSession,
    candidates: list[dict],
    ctx: DebateContext,
) -> bool:
    """Record decision trace. Returns True if escalated to user."""
    best = candidates[0] if candidates else None
    second = candidates[1] if len(candidates) > 1 else None
    score_gap = (best["score"] - second["score"]) if best and second else 1.0

    mode = session.director_mode
    escalate = mode == "advisor" or score_gap < CREATIVE_DIRECTOR_SCORE_GAP_THRESHOLD

    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="decision",
        agent_role="creative_director",
        input_prompt="Select best concept",
        output_content=ctx.last_eval.get("summary", ""),
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="concept",
        decision_context={
            "mode": "advisor" if escalate else "auto",
            "options": [{"label": c["agent_role"], "score": c["score"], "pros": [], "cons": []} for c in candidates],
            "selected": best["agent_role"] if best and not escalate else None,
            "reason": ctx.last_eval.get("summary", ""),
            "confidence": best["score"] if best else 0,
            "escalated_to_user": escalate,
        },
    )
    return escalate


# ── Main orchestrator ──────────────────────────────────────────


def run_debate(session_id: int) -> None:
    """Phase 1: Multi-round concept debate. Runs as BackgroundTask."""
    db = SessionLocal()
    loop = asyncio.new_event_loop()
    try:
        session = db.query(CreativeSession).get(session_id)
        if not session:
            logger.error("[Shorts] Session %d not found", session_id)
            return

        session_ctx = dict(session.context or {})
        ctx = DebateContext(
            topic=session.objective,
            duration=session_ctx.get("duration", 30),
            structure=session_ctx.get("structure", "Monologue"),
            language=session_ctx.get("language", "Korean"),
            max_rounds=session.max_rounds,
            character_name=session_ctx.get("character_name"),
            reference_guidelines=session_ctx.get("reference_guidelines"),
        )

        # Record initial instruction
        seq = get_next_sequence(db, session.id)
        record_trace_sync(
            db,
            session_id=session.id,
            round_number=1,
            sequence=seq,
            trace_type="instruction",
            agent_role="creative_director",
            input_prompt=f"Topic: {ctx.topic}, Duration: {ctx.duration}s, Structure: {ctx.structure}",
            output_content=f"Starting concept debate for '{ctx.topic}' ({ctx.duration}s {ctx.structure})",
            model_id="system",
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            latency_ms=0,
            temperature=0.0,
            phase="concept",
            target_agent="all_architects",
        )
        db.commit()

        # Phase 0: Reference Analyst (optional)
        if session_ctx.get("references"):
            ref_result = loop.run_until_complete(run_reference_analyst(db, session, ctx))
            if ref_result:
                ctx.reference_guidelines = ref_result.get("synthesized_guidelines")
            db.commit()

        # Multi-round debate loop
        for round_num in range(1, ctx.max_rounds + 1):
            logger.info("[Shorts] Session %d: Round %d/%d", session_id, round_num, ctx.max_rounds)

            concepts, critic_result, eval_result = _execute_debate_round(loop, db, session, round_num, ctx)
            ctx.last_eval = eval_result
            ctx.all_round_concepts.append(
                {
                    "round": round_num,
                    "concepts": concepts,
                    "evaluation": eval_result,
                    "critic": critic_result,
                }
            )

            if _check_convergence(eval_result):
                logger.info("[Shorts] Early convergence at round %d", round_num)
                break

            _prepare_next_round(ctx, concepts, eval_result, critic_result)

        # Build candidates and record decision
        candidates = _build_concept_candidates(ctx)
        session.concept_candidates = {"candidates": candidates, "evaluation_summary": ctx.last_eval.get("summary", "")}

        escalated = _record_debate_decision(db, session, candidates, ctx)
        if not escalated and candidates:
            session.selected_concept_index = 0
            session_ctx["selected_concept"] = candidates[0]["concept"]

        session.status = "phase1_done"
        session.context = session_ctx
        session.total_token_usage = calculate_total_tokens(db, session.id)
        db.commit()
        logger.info("[Shorts] Session %d debate complete: %d candidates", session_id, len(candidates))

    except Exception as e:
        logger.exception("[Shorts] Session %d debate failed: %s", session_id, e)
        try:
            session = db.query(CreativeSession).get(session_id)
            if session:
                session.status = "failed"
                db.commit()
        except Exception:
            logger.exception("[Shorts] Failed to record error for session %d", session_id)
    finally:
        loop.close()
        db.close()
