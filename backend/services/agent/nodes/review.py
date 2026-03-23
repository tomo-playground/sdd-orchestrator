"""Review 노드 — 규칙 기반 검증 + 서사 품질 평가 + Gemini 혼합 평가.

Draft 씬의 구조적 유효성을 규칙으로 검증하고,
Full 모드에서 통합 Gemini 호출(기술 + 서사 + 리플렉션)을 1회 수행한다.
통합 호출 실패 시 레거시 개별 호출로 폴백한다.
"""

from __future__ import annotations

import json

from config import LANGGRAPH_AUTO_REVIEW_THRESHOLD, coerce_language_id, coerce_structure_id
from config import pipeline_logger as logger
from config_pipelines import LANGGRAPH_NARRATIVE_THRESHOLD, REVIEW_MODEL
from services.agent.llm_models import (
    NarrativeScoreOutput,
    ReflectionOutput,
    UnifiedReviewOutput,
)
from services.agent.nodes._review_validators import (
    generate_user_summary,
)
from services.agent.nodes._review_validators import (
    validate_scenes as _validate_scenes,
)
from services.agent.observability import record_score
from services.agent.state import NarrativeScore, ReviewResult, ScriptState
from services.llm import LLMConfig, get_llm_provider

_NARRATIVE_WEIGHTS = {
    "hook": 0.25,
    "emotional_arc": 0.15,
    "twist_payoff": 0.10,
    "speaker_tone": 0.05,
    "script_image_sync": 0.10,
    "spoken_naturalness": 0.15,
    "retention_flow": 0.10,
    "pacing_rhythm": 0.10,
}


async def _gemini_evaluate(
    scenes: list[dict],
    topic: str,
    language: str,
) -> str | None:
    """Gemini에 씬 품질 평가를 요청한다. 실패 시 None 반환."""
    try:
        _template_name = "review_evaluate"
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415

        compiled = compile_prompt(
            _template_name,
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            threshold=str(LANGGRAPH_AUTO_REVIEW_THRESHOLD),
        )
        llm_response = await get_llm_provider().generate(
            step_name="evaluate review",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system),
            model=REVIEW_MODEL,
            metadata={"template": _template_name, "mode": "gemini"},
            langfuse_prompt=compiled.langfuse_prompt,
        )
        return llm_response.text
    except Exception as e:
        logger.warning("[LangGraph] Review Gemini 평가 실패: %s", e)
        return None


def _parse_narrative_score(raw: str) -> NarrativeScore | None:
    """Gemini 응답에서 NarrativeScore를 파싱한다. 실패 시 None."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    try:
        parsed = NarrativeScoreOutput.model_validate(data)
    except (ValueError, TypeError):
        return None

    return _build_narrative_score(parsed)


async def _narrative_evaluate(
    scenes: list[dict],
    topic: str,
    language: str,
) -> NarrativeScore | None:
    """서사 품질을 Gemini로 평가한다. 에러 시 None (graceful degradation)."""
    try:
        _template_name_nr = "creative/narrative_review"
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415

        compiled = compile_prompt(
            _template_name_nr,
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            threshold=str(LANGGRAPH_NARRATIVE_THRESHOLD),
        )
        llm_response = await get_llm_provider().generate(
            step_name="evaluate review",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system),
            model=REVIEW_MODEL,
            metadata={"template": _template_name_nr, "mode": "narrative"},
            langfuse_prompt=compiled.langfuse_prompt,
        )
        return _parse_narrative_score(llm_response.text or "")
    except Exception as e:
        logger.warning("[LangGraph] Narrative 평가 실패: %s", e)
        return None


async def _self_reflect(
    review_result: ReviewResult,
    topic: str,
    language: str,
    structure: str,
) -> str | None:
    """Review 실패 시 Self-Reflection을 수행한다 (Phase 10-A)."""
    try:
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415
        from services.agent.prompt_builders_c import (  # noqa: PLC0415
            build_errors_block,
            build_gemini_feedback_section,
            build_narrative_score_section,
            build_warnings_block,
        )

        _template_name_rf = "creative/review_reflection"
        compiled = compile_prompt(
            _template_name_rf,
            topic=topic,
            language=language,
            structure=structure,
            errors_block=build_errors_block(review_result.get("errors", [])),
            warnings_block=build_warnings_block(review_result.get("warnings", [])),
            gemini_feedback_section=build_gemini_feedback_section(review_result.get("gemini_feedback")),
            narrative_score_section=build_narrative_score_section(
                review_result.get("narrative_score"),
                LANGGRAPH_NARRATIVE_THRESHOLD,
            ),
        )
        llm_response = await get_llm_provider().generate(
            step_name="evaluate review",
            contents=compiled.user,
            config=LLMConfig(
                system_instruction=compiled.system
                or "You are a self-reflection agent that analyzes review failures and proposes fix strategies."
            ),
            model=REVIEW_MODEL,
            metadata={"template": _template_name_rf, "mode": "self_reflect"},
            langfuse_prompt=compiled.langfuse_prompt,
        )

        text = (llm_response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(text)

        reflection = f"""[근본 원인]
{data.get("root_cause", "")}

[영향 평가]
{data.get("impact", "")}

[수정 전략]
{data.get("strategy", "")}

[기대 결과]
{data.get("expected_outcome", "")}"""

        logger.info("[LangGraph] Self-Reflection 완료 (근본 원인: %s...)", data.get("root_cause", "")[:50])
        return reflection

    except Exception as e:
        logger.warning("[LangGraph] Self-Reflection 실패: %s", e)
        return None


def _build_narrative_score(parsed: NarrativeScoreOutput) -> NarrativeScore:
    """NarrativeScoreOutput → NarrativeScore TypedDict (overall 재계산)."""
    scores = {k: getattr(parsed, k) for k in _NARRATIVE_WEIGHTS}
    overall = round(sum(scores.get(k, 0.0) * w for k, w in _NARRATIVE_WEIGHTS.items()), 3)
    score = NarrativeScore(**scores, overall=overall, scene_issues=parsed.scene_issues)
    if parsed.feedback:
        score["feedback"] = parsed.feedback
    return score


def _format_reflection(ref: ReflectionOutput) -> str:
    """ReflectionOutput → 구조화된 텍스트."""
    return f"""[근본 원인]
{ref.root_cause}

[영향 평가]
{ref.impact}

[수정 전략]
{ref.strategy}

[기대 결과]
{ref.expected_outcome}"""


async def _unified_evaluate(
    scenes: list[dict],
    topic: str,
    language: str,
    structure: str,
    rule_errors: list[str],
    rule_warnings: list[str],
) -> tuple[UnifiedReviewOutput | None, str | None]:
    """단일 Gemini 호출로 기술 + 서사 + 리플렉션을 통합 평가한다.

    Returns:
        (UnifiedReviewOutput | None, observation_id | None)
    """
    try:
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415
        from services.agent.prompt_builders_c import (  # noqa: PLC0415
            build_rule_errors_section,
            build_rule_warnings_section,
        )

        _template_name_ru = "creative/review_unified"
        compiled = compile_prompt(
            _template_name_ru,
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            structure=structure,
            threshold=str(LANGGRAPH_AUTO_REVIEW_THRESHOLD),
            narrative_threshold=str(LANGGRAPH_NARRATIVE_THRESHOLD),
            rule_errors_section=build_rule_errors_section(rule_errors),
            rule_warnings_section=build_rule_warnings_section(rule_warnings),
        )
        _fallback_sys_ru = "You are a unified review agent that evaluates technical quality, narrative strength, and self-reflection for short-form video scripts."
        llm_response = await get_llm_provider().generate(
            step_name="evaluate review",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system or _fallback_sys_ru),
            model=REVIEW_MODEL,
            metadata={"template": _template_name_ru, "mode": "unified"},
            langfuse_prompt=compiled.langfuse_prompt,
        )

        text = (llm_response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        data = json.loads(text)
        unified = UnifiedReviewOutput.model_validate(data)
        logger.info("[LangGraph] Unified Review 파싱 성공")
        return unified, llm_response.observation_id
    except Exception as e:
        logger.warning("[LangGraph] Unified Review 실패, 레거시 폴백: %s", e)
        return None, None


async def _legacy_evaluate(
    result: ReviewResult,
    scenes: list[dict],
    topic: str,
    language: str,
    structure: str,
) -> tuple[str | None, NarrativeScore | None, str | None]:
    """레거시 개별 Gemini 호출 (폴백용)."""
    gemini_feedback = None
    narrative_score: NarrativeScore | None = None
    reflection: str | None = None

    if not result.get("passed"):
        gemini_feedback = await _gemini_evaluate(scenes, topic, language)
        if gemini_feedback:
            result["gemini_feedback"] = gemini_feedback
        reflection = await _self_reflect(result, topic, language, structure)
    else:
        narrative_score = await _narrative_evaluate(scenes, topic, language)
        if narrative_score:
            result["narrative_score"] = narrative_score
            if narrative_score.get("overall", 1.0) < LANGGRAPH_NARRATIVE_THRESHOLD:
                result["passed"] = False
                reflection = await _self_reflect(result, topic, language, structure)

    return gemini_feedback, narrative_score, reflection


async def review_node(state: ScriptState) -> dict:
    """Draft 씬을 검증하고 review_result를 state에 기록한다."""
    scenes = state.get("draft_scenes") or []
    duration = state.get("duration", 10)
    language = coerce_language_id(state.get("language"))
    structure = coerce_structure_id(state.get("structure"))
    topic = state.get("topic", "")
    is_full = "production" not in (state.get("skip_stages") or [])
    logger.info("[LangGraph:Review] 시작 — scenes=%d, mode=%s", len(scenes), "full" if is_full else "quick")

    result = _validate_scenes(scenes, duration, language, structure)

    gemini_feedback = None
    narrative_score: NarrativeScore | None = None
    reflection: str | None = None

    review_obs_id: str | None = None
    if is_full:
        unified, review_obs_id = await _unified_evaluate(
            scenes,
            topic,
            language,
            structure,
            result.get("errors", []),
            result.get("warnings", []),
        )

        if unified:
            if not unified.technical.passed:
                result["passed"] = False
                gemini_feedback = unified.technical.feedback
                if gemini_feedback:
                    result["gemini_feedback"] = gemini_feedback

            narrative_score = _build_narrative_score(unified.narrative)
            result["narrative_score"] = narrative_score
            if narrative_score.get("overall", 1.0) < LANGGRAPH_NARRATIVE_THRESHOLD:
                result["passed"] = False

            if unified.reflection:
                reflection = _format_reflection(unified.reflection)
        else:
            gemini_feedback, narrative_score, reflection = await _legacy_evaluate(
                result,
                scenes,
                topic,
                language,
                structure,
            )

    result["user_summary"] = generate_user_summary(
        result.get("passed", False),
        len(result.get("errors", [])),
        len(result.get("warnings", [])),
    )

    logger.info(
        "[LangGraph] Review 노드: passed=%s, errors=%d, warnings=%d, gemini=%s, narrative=%.2f, reflection=%s",
        result.get("passed"),
        len(result.get("errors", [])),
        len(result.get("warnings", [])),
        "호출" if gemini_feedback else "건너뜀",
        narrative_score.get("overall", -1) if narrative_score else -1,
        "생성" if reflection else "건너뜀",
    )

    # Score 기록 (Phase 38)
    record_score("first_pass", result.get("passed"), observation_id=review_obs_id)
    record_score("script_qc_issues", len(result.get("errors", [])), observation_id=review_obs_id)
    ns = result.get("narrative_score")
    record_score(
        "narrative_overall",
        ns.get("overall") if ns else None,
        observation_id=review_obs_id,
        comment=json.dumps(ns, ensure_ascii=False) if ns else "",
    )

    # Best scenes 추적: narrative_score가 이전 최고보다 높으면 갱신
    updates: dict = {"review_result": result, "review_reflection": reflection}
    current_overall = narrative_score.get("overall", 0.0) if narrative_score else 0.0
    prev_best = state.get("best_narrative_score", 0.0)
    if current_overall > prev_best and scenes:
        import copy  # noqa: PLC0415

        updates["best_draft_scenes"] = copy.deepcopy(scenes)
        updates["best_narrative_score"] = current_overall
        logger.info("[LangGraph] Best scenes 갱신: %.3f → %.3f", prev_best, current_overall)

    return updates
