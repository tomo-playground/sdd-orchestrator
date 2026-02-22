"""Director Checkpoint 노드 — 스크립트 품질 게이트.

Review 통과 후, Production chain 진입 전에 Director Plan 기준으로
스크립트 품질을 점검한다. proceed/revise 결정.
"""

from __future__ import annotations

from config import logger
from config_pipelines import (
    LANGGRAPH_CHECKPOINT_HIGH_THRESHOLD,
    LANGGRAPH_CHECKPOINT_LOW_THRESHOLD,
    LANGGRAPH_CHECKPOINT_THRESHOLD,
)
from services.agent.llm_models import DirectorCheckpointOutput, validate_with_model
from services.agent.nodes._production_utils import run_production_step
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState


def _apply_score_override(decision: str, score: float, feedback: str) -> tuple[str, str]:
    """Score 기반 decision override (안전망).

    Returns:
        (overridden_decision, overridden_feedback)
    """
    if decision == "proceed" and score < LANGGRAPH_CHECKPOINT_LOW_THRESHOLD:
        feedback = feedback or "구조 재작성 필요 (score < low threshold)"
        logger.warning(
            "[LangGraph] Checkpoint override: proceed→revise (score=%.2f < %.2f)",
            score,
            LANGGRAPH_CHECKPOINT_LOW_THRESHOLD,
        )
        return "revise", feedback

    if decision == "revise" and score >= LANGGRAPH_CHECKPOINT_HIGH_THRESHOLD:
        logger.warning(
            "[LangGraph] Checkpoint override: revise→proceed (score=%.2f >= %.2f)",
            score,
            LANGGRAPH_CHECKPOINT_HIGH_THRESHOLD,
        )
        return "proceed", feedback

    return decision, feedback


async def director_checkpoint_node(state: ScriptState, config=None) -> dict:
    """Director Plan 기준으로 스크립트 품질을 점검한다."""
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "director_checkpoint"):
        return {"director_checkpoint_decision": "proceed"}

    director_plan = state.get("director_plan") or {}
    template_vars = {
        "director_plan": director_plan,
        "draft_scenes": state.get("draft_scenes") or [],
        "review_result": state.get("review_result") or {},
        "topic": state.get("topic", ""),
        "duration": state.get("duration", 30),
        "threshold": LANGGRAPH_CHECKPOINT_THRESHOLD,
    }

    try:
        async with trace_llm_call(name="director_checkpoint", input_text=state.get("topic", "")):
            result = await run_production_step(
                template_name="creative/director_checkpoint.j2",
                template_vars=template_vars,
                validate_fn=lambda data: validate_with_model(DirectorCheckpointOutput, data).model_dump(),
                extract_key="",
                step_name="director_checkpoint",
            )

        cp = DirectorCheckpointOutput.model_validate(result)
        count = state.get("director_checkpoint_revision_count", 0)

        decision, feedback = _apply_score_override(cp.decision, cp.score, cp.feedback)

        logger.info(
            "[LangGraph] Director Checkpoint: decision=%s%s, score=%.2f, revision=%d",
            decision,
            f" (overridden from {cp.decision})" if decision != cp.decision else "",
            cp.score,
            count,
        )

        update: dict = {
            "director_checkpoint_decision": decision,
            "director_checkpoint_score": cp.score,
            "director_checkpoint_revision_count": count + (1 if decision == "revise" else 0),
        }
        if decision == "revise":
            update["director_checkpoint_feedback"] = feedback
            update["revision_feedback"] = feedback
        return update

    except Exception as e:
        logger.warning("[LangGraph] Director Checkpoint 1차 실패: %s", e)
        try:
            async with trace_llm_call(name="director_checkpoint_retry", input_text=state.get("topic", "")):
                result = await run_production_step(
                    template_name="creative/director_checkpoint.j2",
                    template_vars=template_vars,
                    validate_fn=lambda data: validate_with_model(DirectorCheckpointOutput, data).model_dump(),
                    extract_key="",
                    step_name="director_checkpoint_retry",
                )
            cp = DirectorCheckpointOutput.model_validate(result)
            count = state.get("director_checkpoint_revision_count", 0)
            decision, feedback = _apply_score_override(cp.decision, cp.score, cp.feedback)
            update: dict = {
                "director_checkpoint_decision": decision,
                "director_checkpoint_score": cp.score,
                "director_checkpoint_revision_count": count + (1 if decision == "revise" else 0),
            }
            if decision == "revise":
                update["director_checkpoint_feedback"] = feedback
                update["revision_feedback"] = feedback
            return update
        except Exception as retry_err:
            logger.error("[LangGraph] Checkpoint 재시도 실패: %s", retry_err)
            return {
                "director_checkpoint_decision": "error",
                "director_checkpoint_feedback": f"Checkpoint 평가 불가: {retry_err}",
            }
