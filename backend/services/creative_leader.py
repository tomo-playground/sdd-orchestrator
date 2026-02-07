"""Creative Leader — evaluation, direction, and synthesis for debate rounds."""

from __future__ import annotations

import json
import re
from typing import Any

from config import CREATIVE_LEADER_MODEL, logger
from models.creative import CreativeSession
from services.creative_agents import get_provider

# ── Evaluation ───────────────────────────────────────────────


async def evaluate_round(
    session: CreativeSession,
    round_number: int,
    gen_results: list[dict],
    prev_evaluation: dict | None = None,
) -> dict[str, Any]:
    """Leader evaluates all generation outputs and provides direction.

    Returns:
        {
            "summary": str,
            "decision": str,          # continue | converged | terminate
            "scores": {role: {"score": float, "feedback": str}},
            "best_agent_role": str,
            "best_score": float,
            "direction": str,          # next-round guidance
        }
    """
    leader_provider = get_provider("gemini", CREATIVE_LEADER_MODEL)
    criteria = session.evaluation_criteria or {}

    outputs_text = "\n\n".join(
        f"[{r.get('agent_role', 'unknown')}]\n{r.get('content', '')}"
        for r in gen_results
    )

    parts = [
        f"라운드 {round_number} 평가.",
        f"목표: {session.objective}",
        f"평가 기준: {criteria}",
    ]
    if prev_evaluation:
        parts.append(f"이전 라운드 평가: {json.dumps(prev_evaluation, ensure_ascii=False)}")

    parts.append(f"에이전트 결과물:\n{outputs_text}")
    parts.append(
        "각 결과물을 평가하세요. 반드시 JSON으로 응답:\n"
        "- summary(한국어): 이번 라운드 총평\n"
        "- decision: continue/converged/terminate\n"
        "- scores: {agent_role: {score: 0~1, feedback: 한국어 구체적 피드백}}\n"
        "- best_agent_role, best_score\n"
        "- direction(한국어): 다음 라운드에서 에이전트들이 개선해야 할 구체적 방향 지시"
    )

    eval_prompt = "\n\n".join(parts)

    try:
        result = await leader_provider.generate(
            prompt=eval_prompt,
            system_prompt=(
                "당신은 크리에이티브 디렉터입니다. "
                "에이전트의 결과물을 엄격하고 구체적으로 평가하세요. "
                "direction 필드에는 다음 라운드에서 각 에이전트가 "
                "어떤 방향으로 개선해야 하는지 구체적으로 지시하세요. "
                "모든 응답은 한국어로 작성합니다."
            ),
            temperature=0.3,
        )
        raw = result["content"]
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
        parsed = json.loads(cleaned)
        if "direction" not in parsed:
            parsed["direction"] = ""
        return parsed
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("[Creative] Leader evaluation failed: %s, using fallback", e)
        agents = [r.get("agent_role", r.get("role", "unknown")) for r in gen_results]
        return {
            "summary": f"Auto-evaluation (round {round_number})",
            "decision": "continue",
            "scores": {a: {"score": 0.5, "feedback": "Auto-scored"} for a in agents},
            "best_agent_role": agents[0] if agents else None,
            "best_score": 0.5,
            "direction": "",
        }


# ── Synthesis ────────────────────────────────────────────────


async def synthesize_output(
    session: CreativeSession,
    gen_results: list[dict],
    evaluation: dict,
) -> dict[str, Any]:
    """Synthesize a final output combining the best aspects of all agents.

    Called only when decision == "converged".

    Returns:
        {"content": str, "agent_role": "leader_synthesis", "score": float}
    """
    leader_provider = get_provider("gemini", CREATIVE_LEADER_MODEL)

    outputs_text = "\n\n".join(
        f"[{r.get('agent_role', 'unknown')}] (score: {evaluation.get('scores', {}).get(r.get('agent_role', ''), {}).get('score', '?')})\n"
        f"{r.get('content', '')}"
        for r in gen_results
    )

    synth_prompt = (
        f"목표: {session.objective}\n\n"
        f"평가 요약: {evaluation.get('summary', '')}\n\n"
        f"에이전트 결과물:\n{outputs_text}\n\n"
        "위 결과물들의 장점을 결합하여 최종 종합본을 작성하세요. "
        "각 에이전트의 강점을 살리되, 약점은 보완하세요. "
        "종합본만 출력하세요 (메타 설명 없이)."
    )

    try:
        result = await leader_provider.generate(
            prompt=synth_prompt,
            system_prompt=(
                "당신은 크리에이티브 디렉터입니다. "
                "여러 에이전트의 결과물을 종합하여 최상의 최종본을 작성합니다. "
                "모든 응답은 한국어로 작성합니다."
            ),
            temperature=0.4,
        )
        best_score = evaluation.get("best_score", 0.0) or 0.0
        return {
            "content": result["content"],
            "agent_role": "leader_synthesis",
            "score": best_score,
        }
    except (RuntimeError, KeyError, ValueError, TypeError) as e:
        logger.warning("[Creative] Synthesis failed: %s, falling back to best agent", e)
        return {}


# ── Feedback Builder ─────────────────────────────────────────


def build_agent_feedback_context(
    evaluation: dict,
) -> dict[str, str]:
    """Build per-agent feedback strings from evaluation results.

    Returns: {role: feedback_string}
    """
    scores = evaluation.get("scores", {})
    direction = evaluation.get("direction", "")
    result: dict[str, str] = {}

    for role, score_data in scores.items():
        parts = []
        score = score_data.get("score", "?")
        feedback = score_data.get("feedback", "")
        parts.append(f"[이전 라운드 피드백] 점수: {score}, 피드백: {feedback}")
        if direction:
            parts.append(f"[리더 방향 지시] {direction}")
        result[role] = "\n".join(parts)

    return result
