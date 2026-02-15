"""Review 노드 — 규칙 기반 검증 + Gemini 혼합 평가.

Draft 씬의 구조적 유효성을 규칙으로 검증하고,
규칙 실패 시에만 Gemini 평가를 추가 호출한다 (DD-4: 비용 절감).
"""

from __future__ import annotations

import json
import math

from config import (
    LANGGRAPH_AUTO_REVIEW_THRESHOLD,
    REVIEW_SCRIPT_MAX_CHARS_OTHER,
    SCRIPT_LENGTH_KOREAN,
    logger,
    template_env,
)
from services.agent.state import ReviewResult, ScriptState

VALID_SPEAKERS = {"Narrator", "A", "B"}


def _validate_single_scene(
    scene: dict, idx: int, language: str,
) -> tuple[list[str], list[str]]:
    """단일 씬을 검증하고 (errors, warnings) 튜플을 반환한다."""
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
    if isinstance(script, str) and script:
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

    expected_min = math.ceil(duration / 2)
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
    return ReviewResult(passed=passed, errors=errors, warnings=warnings)


async def _gemini_evaluate(
    scenes: list[dict],
    topic: str,
    language: str,
) -> str | None:
    """Gemini에 씬 품질 평가를 요청한다. 실패 시 None 반환."""
    from config import GEMINI_TEXT_MODEL, gemini_client

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
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.warning("[LangGraph] Review Gemini 평가 실패: %s", e)
        return None


async def review_node(state: ScriptState) -> dict:
    """Draft 씬을 검증하고 review_result를 state에 기록한다."""
    scenes = state.get("draft_scenes") or []
    duration = state.get("duration", 10)
    language = state.get("language", "Korean")
    structure = state.get("structure", "Monologue")
    topic = state.get("topic", "")

    result = _validate_scenes(scenes, duration, language, structure)

    # DD-4: 규칙 실패 시에만 Gemini 호출
    gemini_feedback = None
    if not result.get("passed") and state.get("mode") == "full":
        gemini_feedback = await _gemini_evaluate(scenes, topic, language)
        result["gemini_feedback"] = gemini_feedback

    logger.info(
        "[LangGraph] Review 노드: passed=%s, errors=%d, warnings=%d, gemini=%s",
        result.get("passed"),
        len(result.get("errors", [])),
        len(result.get("warnings", [])),
        "호출" if gemini_feedback else "건너뜀",
    )

    return {"review_result": result}
