"""Debate 노드 — Architects → Devil's Advocate → Director 파이프라인 래핑."""

from __future__ import annotations

from config import CREATIVE_MAX_ROUNDS, logger
from database import get_db_session
from models.creative import CreativeSession
from services.agent.state import ScriptState
from services.creative_debate_agents import (
    DebateContext,
    run_architects,
    run_devils_advocate,
    run_director_evaluate,
)


def _build_debate_context(state: ScriptState) -> DebateContext:
    """ScriptState에서 DebateContext를 생성한다."""
    return DebateContext(
        topic=state.get("topic", ""),
        duration=state.get("duration", 10),
        structure=state.get("structure", "Monologue"),
        language=state.get("language", "Korean"),
        max_rounds=CREATIVE_MAX_ROUNDS,
        character_name=None,
        research_brief={"brief": state["research_brief"]} if state.get("research_brief") else None,
    )


def _create_temp_session(db, state: ScriptState) -> CreativeSession:
    """트레이스 기록용 임시 CreativeSession을 DB에 생성한다."""
    session = CreativeSession(
        objective=state.get("topic", "LangGraph debate"),
        evaluation_criteria={"source": "langgraph_debate"},
        context={"mode": state.get("mode", "full")},
        max_rounds=CREATIVE_MAX_ROUNDS,
        status="debating",
        session_type="shorts",
        director_mode="autonomous",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _extract_winner(concepts: list[dict], evaluation: dict) -> dict:
    """Director 평가에서 승리 컨셉을 추출한다."""
    best_role = evaluation.get("best_agent_role")
    for c in concepts:
        if c.get("agent_role") == best_role:
            return c
    return concepts[0] if concepts else {}


async def debate_node(state: ScriptState) -> dict:
    """Debate 파이프라인을 실행하고 결과를 state에 기록한다."""
    with get_db_session() as db:
        try:
            ctx = _build_debate_context(state)
            session = _create_temp_session(db, state)
            round_number = 1

            # 1) Architects: 3인 병렬 컨셉 생성
            concepts = await run_architects(db, session, round_number, ctx)
            if not concepts:
                logger.warning("[LangGraph] Debate: Architects가 컨셉을 생성하지 못함")
                return {"error": "Debate architects produced no concepts"}

            # 2) Devil's Advocate: 비판적 검토
            critic = await run_devils_advocate(db, session, round_number, concepts, ctx)
            if critic:
                ctx.critic_feedback = critic

            # 3) Director Evaluate: 최종 평가
            evaluation = await run_director_evaluate(db, session, round_number, concepts, ctx)
            winner = _extract_winner(concepts, evaluation)

            session.status = "completed"
            db.commit()

            logger.info(
                "[LangGraph] Debate 노드 완료: winner=%s, score=%.2f",
                evaluation.get("best_agent_role", "unknown"),
                evaluation.get("best_score", 0),
            )

            return {
                "debate_result": {
                    "selected_concept": winner,
                    "candidates": concepts,
                    "evaluation": evaluation,
                }
            }

        except Exception as e:
            logger.error("[LangGraph] Debate 노드 실패: %s", e)
            return {"error": f"Debate failed: {e}"}
