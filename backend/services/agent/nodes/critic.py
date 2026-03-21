"""Critic 노드 — 3인 Architect 실시간 토론 (Phase 10-C-3)."""

from __future__ import annotations

import json
import time

from config import CREATIVE_MAX_ROUNDS, coerce_language_id, coerce_structure_id
from config import pipeline_logger as logger
from config_pipelines import DEBATE_TIMEOUT_SEC, MAX_DEBATE_ROUNDS
from database import get_db_session
from models.creative import CreativeSession
from services.agent.nodes._debate_utils import _check_convergence, _concepts_too_similar
from services.agent.state import ScriptState
from services.creative_debate_agents import (
    ARCHITECT_PERSPECTIVES,
    DebateContext,
    run_architects,
    run_director_evaluate,
)
from services.creative_utils import parse_json_response

_EMPTY_RESULT: dict = {"critic_result": None, "debate_log": []}


def _detect_groupthink(concepts: list[dict]) -> bool:
    """컨셉 리스트에서 Groupthink 여부를 감지한다."""
    return _concepts_too_similar(concepts)


def _normalize_research_brief(research_brief) -> dict | None:
    """research_brief를 dict로 정규화한다 (str/dict/None 대응)."""
    if isinstance(research_brief, dict):
        return research_brief
    if isinstance(research_brief, str) and research_brief.strip():
        return {"topic_summary": research_brief}
    return None


def _build_debate_context(state: ScriptState) -> DebateContext:
    """ScriptState에서 DebateContext를 생성한다."""
    research_brief = _normalize_research_brief(state.get("research_brief"))
    casting = state.get("casting_recommendation") or {}
    return DebateContext(
        topic=state.get("topic", ""),
        duration=state.get("duration", 10),
        structure=coerce_structure_id(state.get("structure")),
        language=coerce_language_id(state.get("language")),
        max_rounds=CREATIVE_MAX_ROUNDS,
        character_name=casting.get("character_a_name") or None,
        character_b_name=casting.get("character_b_name") or None,
        research_brief=research_brief,
        director_plan=state.get("director_plan"),
    )


def _create_temp_session(db, state: ScriptState) -> CreativeSession:
    """트레이스 기록용 임시 CreativeSession을 DB에 생성한다."""
    session = CreativeSession(
        objective=state.get("topic", "LangGraph critic"),
        evaluation_criteria={"source": "langgraph_critic"},
        context={"skip_stages": state.get("skip_stages", [])},
        max_rounds=CREATIVE_MAX_ROUNDS,
        status="debating",
        session_type="shorts",
        director_mode="autonomous",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _parse_candidates(raw_results: list[dict]) -> list[dict]:
    """generate_parallel 결과에서 content JSON을 파싱하여 flat candidate로 변환한다."""
    parsed = []
    for r in raw_results:
        content = r.get("content", "")
        try:
            data = parse_json_response(content) if isinstance(content, str) else content
        except (json.JSONDecodeError, KeyError):
            data = {}
        candidate = {
            "agent_role": r.get("agent_role", "unknown"),
            "title": data.get("title", ""),
            "concept": data.get("hook", ""),
            "hook_strength": data.get("hook_strength", ""),
            "arc": data.get("arc", ""),
            "mood_progression": data.get("mood_progression", ""),
            "pacing_note": data.get("pacing_note", ""),
            "estimated_scenes": data.get("estimated_scenes"),
            "key_moments": data.get("key_moments", []),
            "strengths": [m.get("description", "") for m in (data.get("key_moments") or [])[:2]],
        }
        parsed.append(candidate)
    return parsed


def _extract_winner(concepts: list[dict], evaluation: dict) -> dict:
    """Director 평가에서 승리 컨셉을 추출한다."""
    best_role = evaluation.get("best_agent_role")
    for c in concepts:
        if c.get("agent_role") == best_role:
            return c
    return concepts[0] if concepts else {}


def _build_critique_feedback(concepts: list[dict], critique_for_role: str) -> dict:
    """특정 Architect가 받을 비평 피드백을 구성한다.

    Args:
        concepts: 현재 라운드의 전체 컨셉 리스트
        critique_for_role: 비평을 받을 Architect role (예: "emotional_arc")

    Returns:
        by_role dict (다른 2인의 비평 요약)
    """
    # 다른 2인의 컨셉을 요약하여 전달
    other_concepts = [c for c in concepts if c.get("agent_role") != critique_for_role]

    critique_text = "다른 Architect들의 컨셉:\n"
    for c in other_concepts:
        critique_text += f"- {c.get('agent_role')}: {c.get('title', '')}\n"
        critique_text += f"  → {c.get('concept', '')[:100]}...\n"

    critique_text += "\n이 컨셉들을 참고하여 당신의 컨셉을 개선하세요. "
    critique_text += "다른 접근과 차별화하되, 좋은 아이디어는 흡수하세요."

    return {"by_role": {critique_for_role: critique_text}}


async def _run_debate_round(
    db,
    session: CreativeSession,
    round_num: int,
    ctx: DebateContext,
    prev_concepts: list[dict] | None,
) -> list[dict]:
    """단일 토론 라운드를 실행한다.

    Args:
        db: DB 세션
        session: CreativeSession
        round_num: 라운드 번호 (1부터 시작)
        ctx: DebateContext
        prev_concepts: 이전 라운드 컨셉 (None이면 첫 라운드)

    Returns:
        현재 라운드의 컨셉 리스트
    """
    # 이전 라운드 컨셉을 역할별로 매핑
    if prev_concepts:
        ctx.prev_concepts = {c.get("agent_role"): c for c in prev_concepts}

        # 각 Architect에게 다른 2인의 컨셉을 비평 피드백으로 전달 (전 role 누적)
        all_feedback: dict[str, str] = {}
        for arch in ARCHITECT_PERSPECTIVES:
            role = arch["role"]
            fb = _build_critique_feedback(prev_concepts, role)
            all_feedback.update(fb.get("by_role", {}))
        ctx.critic_feedback = {"by_role": all_feedback}

    # Architects 병렬 실행
    raw_results = await run_architects(db, session, round_num, ctx)

    # 파싱
    concepts = _parse_candidates(raw_results)

    return concepts


async def critic_node(state: ScriptState) -> dict:
    """Critic 파이프라인 — 3인 Architect 실시간 토론 (Phase 10-C-3).

    Phase 10-C-3:
    - Round 1: 각 Architect 독립 컨셉 생성
    - Round 2+: 상호 비평 및 컨셉 개선 (최대 MAX_DEBATE_ROUNDS)
    - KPI 기반 수렴 판단 (NarrativeScore, Hook 강도)
    - Groupthink 방지 (다양성 강제)
    - Hard Timeout + Fallback
    """
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "critic"):
        return {"critic_result": None, "debate_log": []}

    start_time = time.time()
    debate_log: list[dict] = []
    concepts: list[dict] = []  # Initialize to avoid unbound variable

    with get_db_session() as db:
        try:
            ctx = _build_debate_context(state)
            session = _create_temp_session(db, state)

            # Round 1: 독립 컨셉 생성
            logger.info("[LangGraph] Critic 토론 Round 1: 독립 컨셉 생성")
            concepts = await _run_debate_round(db, session, round_num=1, ctx=ctx, prev_concepts=None)

            if not concepts:
                logger.warning("[LangGraph] Critic: Architects가 컨셉을 생성하지 못함 (graceful)")
                return _EMPTY_RESULT

            debate_log.append(
                {
                    "round": 1,
                    "action": "propose",
                    "concepts": [{"role": c.get("agent_role"), "title": c.get("title")} for c in concepts],
                }
            )

            # Round 2+: 상호 비평 및 개선
            for round_num in range(2, MAX_DEBATE_ROUNDS + 2):  # +2 because range is exclusive
                # Timeout 체크
                elapsed = time.time() - start_time
                if elapsed > DEBATE_TIMEOUT_SEC:
                    logger.warning("[Debate] Timeout 도달 (%.1f초) — 현재 최선 선택", elapsed)
                    debate_log.append(
                        {
                            "round": round_num,
                            "action": "timeout",
                            "elapsed_sec": elapsed,
                        }
                    )
                    break

                # 수렴 판단
                converged = await _check_convergence(concepts, debate_log, round_num - 1)
                if converged:
                    logger.info("[Debate] 수렴 판단 (Round %d) — 토론 종료", round_num - 1)
                    debate_log.append(
                        {
                            "round": round_num - 1,
                            "action": "converged",
                        }
                    )
                    break

                # 비평 라운드 실행
                logger.info("[LangGraph] Critic 토론 Round %d: 상호 비평", round_num)
                refined_concepts = await _run_debate_round(
                    db, session, round_num=round_num, ctx=ctx, prev_concepts=concepts
                )

                debate_log.append(
                    {
                        "round": round_num,
                        "action": "critique_refine",
                        "concepts": [{"role": c.get("agent_role"), "title": c.get("title")} for c in refined_concepts],
                        "groupthink_detected": _detect_groupthink(refined_concepts),
                    }
                )

                concepts = refined_concepts

            # Director 최종 평가
            logger.info("[LangGraph] Critic: Director 최종 평가")
            # Convert concepts to the format expected by run_director_evaluate
            formatted_concepts = [
                {"agent_role": c.get("agent_role"), "content": json.dumps(c, ensure_ascii=False)} for c in concepts
            ]
            evaluation = await run_director_evaluate(
                db,
                session,
                round_number=1,
                concepts=formatted_concepts,
                ctx=ctx,
            )

            winner = _extract_winner(concepts, evaluation)

            session.status = "completed"
            db.commit()

            elapsed_total = time.time() - start_time
            logger.info(
                "[LangGraph] Critic 토론 완료: winner=%s, rounds=%d, elapsed=%.1fs",
                evaluation.get("best_agent_role", "unknown"),
                len(debate_log),
                elapsed_total,
            )

            return {
                "critic_result": {
                    "selected_concept": winner,
                    "candidates": concepts,
                    "evaluation": evaluation,
                },
                "debate_log": debate_log,  # Phase 10-C-3: 토론 과정 기록
            }

        except TimeoutError:
            # Hard Timeout — 현재까지의 최선 선택
            logger.error("[LangGraph] Critic 토론 Timeout — Fallback to existing pipeline")
            # Fallback: 기존 단순 파이프라인 (single-shot)
            # 현재까지의 concepts가 있으면 그것으로, 없으면 에러
            if concepts:
                return {
                    "critic_result": {
                        "selected_concept": concepts[0],
                        "candidates": concepts,
                        "evaluation": {"fallback": True, "reason": "timeout"},
                    },
                    "debate_log": debate_log,
                }
            logger.warning("[LangGraph] Critic timeout + no concepts (graceful)")
            return _EMPTY_RESULT

        except Exception as e:
            logger.warning("[LangGraph] Critic 노드 실패 (graceful): %s", e)
            return _EMPTY_RESULT
