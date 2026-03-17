"""Review 노드 — 규칙 기반 검증 + 서사 품질 평가 + Gemini 혼합 평가.

Draft 씬의 구조적 유효성을 규칙으로 검증하고,
Full 모드에서 통합 Gemini 호출(기술 + 서사 + 리플렉션)을 1회 수행한다.
통합 호출 실패 시 레거시 개별 호출로 폴백한다.
"""

from __future__ import annotations

import json

from config import (
    DURATION_DEFICIT_THRESHOLD,
    DURATION_OVERFLOW_THRESHOLD,
    LANGGRAPH_AUTO_REVIEW_THRESHOLD,
    REVIEW_SCRIPT_MAX_CHARS_OTHER,
    SCRIPT_LENGTH_KOREAN,
    logger,
)
from config_pipelines import LANGGRAPH_NARRATIVE_THRESHOLD, REVIEW_MODEL
from services.agent.llm_models import (
    NarrativeScoreOutput,
    ReflectionOutput,
    UnifiedReviewOutput,
)
from services.agent.state import NarrativeScore, ReviewResult, ScriptState
from services.llm import LLMConfig, get_llm_provider
from services.storyboard.helpers import calculate_min_scenes, normalize_structure

VALID_SPEAKERS = {"Narrator", "A", "B"}


def _generate_user_summary(passed: bool, error_count: int, warning_count: int) -> str:
    """사용자용 요약 메시지를 생성한다.

    - 검증 통과: 긍정적 메시지
    - 경고만: 개선 중 메시지
    - 오류 있음: 재생성 안내
    """
    if passed:
        if warning_count > 0:
            return f"✅ 검증 완료 (경고 {warning_count}개는 자동 개선됩니다)"
        return "✅ 검증 완료"

    if error_count > 0:
        return f"🔄 AI가 시나리오를 개선하고 있습니다 (문제 {error_count}개 수정 중)"

    return "🔄 시나리오 품질을 개선하고 있습니다"


def _validate_single_scene(
    scene: dict,
    idx: int,
    language: str,
) -> tuple[list[str], list[str]]:
    """단일 씬을 검증하고 (errors, warnings) 튜플을 반환한다.

    errors/warnings는 Revise 노드가 파싱하여 자동 수정에 사용한다.
    사용자용 메시지는 user_summary로 별도 생성.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for field in ("script", "speaker", "duration", "image_prompt"):
        if field not in scene or scene[field] is None:
            errors.append(f"씬 {idx}: 필수 필드 '{field}' 누락")

    speaker = scene.get("speaker")
    if speaker and speaker not in VALID_SPEAKERS:
        errors.append(f"씬 {idx}: 유효하지 않은 speaker '{speaker}' (허용: {VALID_SPEAKERS})")

    scene_dur = scene.get("duration")
    if isinstance(scene_dur, (int, float)) and scene_dur <= 0:
        errors.append(f"씬 {idx}: duration이 0 이하 ({scene_dur})")

    script = scene.get("script", "")
    if isinstance(script, str):
        stripped = script.replace(".", "").replace(" ", "").strip()
        if not stripped:
            errors.append(f"씬 {idx}: 빈 스크립트 ('{script}')")
        elif len(stripped) < 5:
            warnings.append(f"씬 {idx}: 스크립트 너무 짧음 ({len(script)}자)")
        max_len = SCRIPT_LENGTH_KOREAN[1] if language == "Korean" else REVIEW_SCRIPT_MAX_CHARS_OTHER
        if len(script) > max_len:
            warnings.append(f"씬 {idx}: 스크립트 길이 초과 ({len(script)}자 > {max_len}자)")

    img_prompt = scene.get("image_prompt")
    if isinstance(img_prompt, str) and not img_prompt.strip():
        warnings.append(f"씬 {idx}: image_prompt가 비어있음")

    return errors, warnings


def _validate_scenes(
    scenes: list[dict],
    duration: int,
    language: str,
    structure: str,
) -> ReviewResult:
    """씬 목록을 검증하고 ReviewResult를 반환한다 (순수 함수)."""
    errors: list[str] = []
    warnings: list[str] = []

    structure = normalize_structure(structure)
    expected_min = calculate_min_scenes(duration, structure)
    if len(scenes) < expected_min:
        errors.append(f"씬 개수 부족: {len(scenes)}개 (최소 {expected_min}개 필요, duration={duration}s)")

    # 총 duration 검증: 목표의 DURATION_DEFICIT_THRESHOLD 미만이면 에러
    total_dur = sum(s.get("duration", 0) for s in scenes)
    threshold = duration * DURATION_DEFICIT_THRESHOLD
    if duration > 0 and total_dur < threshold:
        errors.append(f"총 duration 부족: {total_dur:.1f}s (목표 {duration}s의 85% = {threshold:.1f}s 미달)")

    # 총 duration 검증: 목표의 DURATION_OVERFLOW_THRESHOLD 초과이면 에러
    overflow_limit = duration * DURATION_OVERFLOW_THRESHOLD
    if duration > 0 and total_dur > overflow_limit:
        errors.append(
            f"총 duration 초과: {total_dur:.1f}s (목표 {duration}s의 {DURATION_OVERFLOW_THRESHOLD * 100:.0f}% = {overflow_limit:.1f}s 초과)"
        )

    speakers_found: set[str] = set()
    for i, scene in enumerate(scenes):
        scene_errors, scene_warnings = _validate_single_scene(scene, i + 1, language)
        errors.extend(scene_errors)
        warnings.extend(scene_warnings)
        speaker = scene.get("speaker")
        if speaker:
            speakers_found.add(speaker)

    if structure in ("Monologue", "Confession"):
        invalid = speakers_found - {"A", "Narrator"}
        if invalid:
            errors.append(
                f"{structure}는 speaker='A' 또는 'Narrator'만 허용 — 잘못된 speaker 발견: {', '.join(sorted(invalid))}"
            )
    elif structure.replace("_", " ") in ("Dialogue", "Narrated Dialogue"):
        for s in ("A", "B"):
            if s not in speakers_found:
                errors.append(f"Dialogue 구조에서 speaker '{s}'가 등장하지 않음 — 반드시 A와 B 모두 포함해야 함")

        # (a) Speaker 비율 검증: A,B 모두 존재할 때만 비율 검사 (누락은 위에서 별도 처리)
        non_narrator = [sc for sc in scenes if sc.get("speaker") in ("A", "B")]
        if "A" in speakers_found and "B" in speakers_found and len(non_narrator) >= 2:
            a_count = sum(1 for sc in non_narrator if sc.get("speaker") == "A")
            b_count = len(non_narrator) - a_count
            total = len(non_narrator)
            for label, cnt in [("A", a_count), ("B", b_count)]:
                pct = cnt / total * 100
                if pct < 20:
                    errors.append(
                        f"Dialogue 구조에서 speaker 비율 불균형 — {label}가 {pct:.0f}%로 최소 20% 미만 (A={a_count}, B={b_count}, 총 {total}씬)"
                    )

        # (b) Narrator 존재 검증 (Narrated Dialogue 전용)
        if structure.replace("_", " ") == "Narrated Dialogue":
            if "Narrator" not in speakers_found:
                warnings.append(
                    f"Narrated Dialogue에서 Narrator 씬 없음 — 환경/분위기 묘사 씬 권장 (현재 {len(scenes)}씬 모두 캐릭터)"
                )

    passed = len(errors) == 0

    # 사용자용 요약 메시지 생성
    user_summary = _generate_user_summary(passed, len(errors), len(warnings))

    return ReviewResult(passed=passed, errors=errors, warnings=warnings, user_summary=user_summary)


async def _gemini_evaluate(
    scenes: list[dict],
    topic: str,
    language: str,
) -> str | None:
    """Gemini에 씬 품질 평가를 요청한다. 실패 시 None 반환."""
    try:
        _template_name = "review_evaluate.j2"
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415

        compiled = compile_prompt(
            _template_name,
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            threshold=str(LANGGRAPH_AUTO_REVIEW_THRESHOLD),
        )
        llm_response = await get_llm_provider().generate(
            step_name="review_gemini_evaluate",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system),
            model=REVIEW_MODEL,
            metadata={"template": _template_name},
            langfuse_prompt=compiled.langfuse_prompt,
        )
        return llm_response.text
    except Exception as e:
        logger.warning("[LangGraph] Review Gemini 평가 실패: %s", e)
        return None


_NARRATIVE_WEIGHTS = {
    "hook": 0.30,
    "emotional_arc": 0.25,
    "twist_payoff": 0.15,
    "speaker_tone": 0.20,
    "script_image_sync": 0.10,
}


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
        _template_name_nr = "creative/narrative_review.j2"
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415

        compiled = compile_prompt(
            _template_name_nr,
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            threshold=str(LANGGRAPH_NARRATIVE_THRESHOLD),
        )
        llm_response = await get_llm_provider().generate(
            step_name="review_narrative_evaluate",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system),
            model=REVIEW_MODEL,
            metadata={"template": _template_name_nr},
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
    """Review 실패 시 Self-Reflection을 수행한다 (Phase 10-A).

    근본 원인 분석 + 구체적 수정 전략을 Gemini에 요청한다.
    실패 시 None 반환 (graceful degradation).
    """
    try:
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415
        from services.agent.prompt_builders_c import (  # noqa: PLC0415
            build_errors_block,
            build_gemini_feedback_section,
            build_narrative_score_section,
            build_warnings_block,
        )

        _template_name_rf = "creative/review_reflection.j2"
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
            step_name="review_self_reflect",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system or "You are a self-reflection agent that analyzes review failures and proposes fix strategies."),
            model=REVIEW_MODEL,
            metadata={"template": _template_name_rf},
            langfuse_prompt=compiled.langfuse_prompt,
        )

        # JSON 파싱
        text = (llm_response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(text)

        # 구조화된 reflection 텍스트 생성
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
    score = NarrativeScore(**scores, overall=overall)
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
) -> UnifiedReviewOutput | None:
    """단일 Gemini 호출로 기술 + 서사 + 리플렉션을 통합 평가한다.

    실패 시 None 반환 (레거시 개별 호출로 폴백).
    """
    try:
        from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415
        from services.agent.prompt_builders_c import (  # noqa: PLC0415
            build_rule_errors_section,
            build_rule_warnings_section,
        )

        _template_name_ru = "creative/review_unified.j2"
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
            step_name="review_unified_evaluate",
            contents=compiled.user,
            config=LLMConfig(
                system_instruction=compiled.system or _fallback_sys_ru,
            ),
            model=REVIEW_MODEL,
            metadata={"template": _template_name_ru},
            langfuse_prompt=compiled.langfuse_prompt,
        )

        text = (llm_response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        data = json.loads(text)
        unified = UnifiedReviewOutput.model_validate(data)
        logger.info("[LangGraph] Unified Review 파싱 성공")
        return unified
    except Exception as e:
        logger.warning("[LangGraph] Unified Review 실패, 레거시 폴백: %s", e)
        return None


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
    """Draft 씬을 검증하고 review_result를 state에 기록한다.

    Phase 13-A: 통합 Gemini 호출 (기술 + 서사 + 리플렉션) 1회.
    통합 호출 실패 시 레거시 개별 호출로 폴백.
    """
    scenes = state.get("draft_scenes") or []
    duration = state.get("duration", 10)
    language = state.get("language", "Korean")
    structure = state.get("structure", "Monologue")
    topic = state.get("topic", "")
    is_full = "production" not in (state.get("skip_stages") or [])

    result = _validate_scenes(scenes, duration, language, structure)

    gemini_feedback = None
    narrative_score: NarrativeScore | None = None
    reflection: str | None = None

    if is_full:
        unified = await _unified_evaluate(
            scenes,
            topic,
            language,
            structure,
            result.get("errors", []),
            result.get("warnings", []),
        )

        if unified:
            # 통합 응답 처리
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
            # 폴백: 레거시 개별 호출
            gemini_feedback, narrative_score, reflection = await _legacy_evaluate(
                result,
                scenes,
                topic,
                language,
                structure,
            )

    # user_summary 갱신 (narrative_score 실패 등 후속 판정 반영)
    result["user_summary"] = _generate_user_summary(
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

    return {"review_result": result, "review_reflection": reflection}
