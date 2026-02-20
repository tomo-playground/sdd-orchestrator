"""Review 노드 — 규칙 기반 검증 + 서사 품질 평가 + Gemini 혼합 평가.

Draft 씬의 구조적 유효성을 규칙으로 검증하고,
규칙 실패 시에만 Gemini 평가를 추가 호출한다 (DD-4: 비용 절감).
Full 모드에서 규칙 통과 시 서사 품질(NarrativeScore)을 추가 평가한다.
"""

from __future__ import annotations

import json

from config import (
    LANGGRAPH_AUTO_REVIEW_THRESHOLD,
    REVIEW_SCRIPT_MAX_CHARS_OTHER,
    SCRIPT_LENGTH_KOREAN,
    logger,
    template_env,
)
from config_pipelines import LANGGRAPH_NARRATIVE_THRESHOLD, REVIEW_MODEL
from services.agent.llm_models import NarrativeScoreOutput
from services.agent.observability import trace_llm_call
from services.agent.state import NarrativeScore, ReviewResult, ScriptState
from services.storyboard.helpers import calculate_min_scenes

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

    expected_min = calculate_min_scenes(duration)
    if len(scenes) < expected_min:
        errors.append(f"씬 개수 부족: {len(scenes)}개 (최소 {expected_min}개 필요, duration={duration}s)")

    speakers_found: set[str] = set()
    for i, scene in enumerate(scenes):
        scene_errors, scene_warnings = _validate_single_scene(scene, i + 1, language)
        errors.extend(scene_errors)
        warnings.extend(scene_warnings)
        speaker = scene.get("speaker")
        if speaker:
            speakers_found.add(speaker)

    if structure in ("Dialogue", "Narrated Dialogue"):
        for s in ("A", "B"):
            if s not in speakers_found:
                warnings.append(f"Dialogue 구조에서 speaker '{s}'가 등장하지 않음")

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
    from config import gemini_client

    if not gemini_client:
        logger.warning("[LangGraph] Review: Gemini 클라이언트 없음, 평가 건너뜀")
        return None

    try:
        tmpl = template_env.get_template("review_evaluate.j2")
        prompt = tmpl.render(
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            threshold=LANGGRAPH_AUTO_REVIEW_THRESHOLD,
        )
        async with trace_llm_call(name="review_gemini_evaluate", input_text=prompt[:2000], model=REVIEW_MODEL) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=REVIEW_MODEL,
                contents=prompt,
            )
            llm.record(response)
        return response.text
    except Exception as e:
        logger.warning("[LangGraph] Review Gemini 평가 실패: %s", e)
        return None


_NARRATIVE_WEIGHTS = {
    "hook": 0.35,
    "emotional_arc": 0.25,
    "twist_payoff": 0.15,
    "speaker_tone": 0.10,
    "script_image_sync": 0.15,
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

    scores = {k: getattr(parsed, k) for k in _NARRATIVE_WEIGHTS}
    overall = round(sum(scores.get(k, 0.0) * w for k, w in _NARRATIVE_WEIGHTS.items()), 3)

    score = NarrativeScore(**scores, overall=overall)
    if parsed.feedback:
        score["feedback"] = parsed.feedback
    return score


async def _narrative_evaluate(
    scenes: list[dict],
    topic: str,
    language: str,
) -> NarrativeScore | None:
    """서사 품질을 Gemini로 평가한다. 에러 시 None (graceful degradation)."""
    from config import gemini_client

    if not gemini_client:
        logger.warning("[LangGraph] Narrative: Gemini 클라이언트 없음, 건너뜀")
        return None

    try:
        tmpl = template_env.get_template("creative/narrative_review.j2")
        prompt = tmpl.render(
            scenes=json.dumps(scenes, ensure_ascii=False),
            topic=topic,
            language=language,
            threshold=LANGGRAPH_NARRATIVE_THRESHOLD,
        )
        async with trace_llm_call(
            name="review_narrative_evaluate", input_text=prompt[:2000], model=REVIEW_MODEL
        ) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=REVIEW_MODEL,
                contents=prompt,
            )
            llm.record(response)
        return _parse_narrative_score(response.text or "")
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
    from config import gemini_client

    if not gemini_client:
        logger.warning("[LangGraph] Self-Reflection: Gemini 클라이언트 없음, 건너뜀")
        return None

    try:
        tmpl = template_env.get_template("creative/review_reflection.j2")
        prompt = tmpl.render(
            topic=topic,
            language=language,
            structure=structure,
            errors=review_result.get("errors", []),
            warnings=review_result.get("warnings", []),
            gemini_feedback=review_result.get("gemini_feedback"),
            narrative_score=review_result.get("narrative_score"),
            narrative_threshold=LANGGRAPH_NARRATIVE_THRESHOLD,
        )
        async with trace_llm_call(name="review_self_reflect", input_text=prompt[:2000], model=REVIEW_MODEL) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=REVIEW_MODEL,
                contents=prompt,
            )
            llm.record(response)

        # JSON 파싱
        text = (response.text or "").strip()
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


async def review_node(state: ScriptState) -> dict:
    """Draft 씬을 검증하고 review_result를 state에 기록한다.

    3-tier 검증 (Full 모드):
      1. 규칙 기반 검증
      2. 규칙 실패 → Gemini 피드백
      3. 규칙 통과 → 서사 품질 평가 (NarrativeScore)

    Phase 10-A:
      4. 실패 시 → Self-Reflection (근본 원인 분석 + 수정 전략)
    """
    scenes = state.get("draft_scenes") or []
    duration = state.get("duration", 10)
    language = state.get("language", "Korean")
    structure = state.get("structure", "Monologue")
    topic = state.get("topic", "")
    is_full = state.get("mode") == "full"

    result = _validate_scenes(scenes, duration, language, structure)

    gemini_feedback = None
    narrative_score: NarrativeScore | None = None
    reflection: str | None = None

    if is_full:
        if not result.get("passed"):
            # 규칙 실패: Gemini 평가 + Self-Reflection (서사 평가는 건너뜀)
            gemini_feedback = await _gemini_evaluate(scenes, topic, language)
            if gemini_feedback:
                result["gemini_feedback"] = gemini_feedback
            reflection = await _self_reflect(result, topic, language, structure)
        else:
            # 규칙 통과: 서사 품질 평가만
            narrative_score = await _narrative_evaluate(scenes, topic, language)
            if narrative_score:
                result["narrative_score"] = narrative_score
                if narrative_score.get("overall", 1.0) < LANGGRAPH_NARRATIVE_THRESHOLD:
                    result["passed"] = False
                    # 서사 품질 미달 → Self-Reflection
                    reflection = await _self_reflect(result, topic, language, structure)

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
