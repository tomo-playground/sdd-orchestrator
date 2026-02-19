"""Director Checkpoint 노드 — 스크립트 품질 게이트.

Review 통과 후, Production chain 진입 전에 Director Plan 기준으로
스크립트 품질을 점검한다. proceed/revise 결정.
"""

from __future__ import annotations

from config import logger
from config_pipelines import LANGGRAPH_CHECKPOINT_THRESHOLD
from services.agent.nodes._production_utils import run_production_step
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState


def _validate_checkpoint(result: dict | list | str) -> dict:
    """Checkpoint 응답 검증: decision, score, reasoning 필수."""
    if not isinstance(result, dict):
        return {"ok": False, "issues": ["Response must be a JSON object"], "checks": {}}

    missing = []
    decision = result.get("decision")
    if decision not in ("proceed", "revise"):
        missing.append("decision (proceed|revise)")
    if result.get("score") is None:
        missing.append("score")
    if not result.get("reasoning"):
        missing.append("reasoning")
    if decision == "revise" and not result.get("feedback"):
        missing.append("feedback (revise 시 필수)")

    if missing:
        return {"ok": False, "issues": [f"Missing: {', '.join(missing)}"], "checks": {}}
    return {"ok": True, "issues": [], "checks": {}}


async def director_checkpoint_node(state: ScriptState, config=None) -> dict:
    """Director Plan 기준으로 스크립트 품질을 점검한다."""
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
                validate_fn=_validate_checkpoint,
                extract_key="",
                step_name="director_checkpoint",
            )

        decision = result.get("decision", "proceed")
        score = float(result.get("score", 0.0))
        feedback = result.get("feedback", "")
        count = state.get("director_checkpoint_revision_count", 0)

        logger.info(
            "[LangGraph] Director Checkpoint: decision=%s, score=%.2f, revision=%d",
            decision,
            score,
            count,
        )

        update: dict = {
            "director_checkpoint_decision": decision,
            "director_checkpoint_score": score,
            "director_checkpoint_revision_count": count + (1 if decision == "revise" else 0),
        }
        if decision == "revise":
            update["director_checkpoint_feedback"] = feedback
            update["revision_feedback"] = feedback
        return update

    except Exception as e:
        logger.warning("[LangGraph] Director Checkpoint 실패, 자동 통과: %s", e)
        return {"director_checkpoint_decision": "proceed"}
