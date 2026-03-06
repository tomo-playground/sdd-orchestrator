"""Topic analysis service — Gemini 기반 토픽 분석 및 설정 추천."""

from __future__ import annotations

from config import logger
from schemas import TopicAnalyzeResponse


async def analyze_topic(
    topic: str,
    description: str | None,
    group_id: int | None,  # noqa: ARG001 — 라우터 시그니처 유지
    messages: list[dict] | None = None,
) -> TopicAnalyzeResponse:
    """토픽을 분석하여 최적의 영상 설정을 추천한다.

    대화 이력(messages)이 있으면 맥락을 유지하며,
    정보가 부족하면 clarify 질문을 반환한다.
    """
    from config import (
        GEMINI_SAFETY_SETTINGS,
        GEMINI_TEXT_MODEL,
        SHORTS_DURATIONS,
        STORYBOARD_LANGUAGES,
        gemini_client,
        template_env,
    )
    from services.agent.inventory import STRUCTURE_METADATA
    from services.creative_utils import parse_json_response

    # 인라인 편집용 옵션 목록 구성 (캐릭터/구성은 Director SSOT → 여기서 불필요)
    available_options = _build_options()
    fallback = TopicAnalyzeResponse(
        duration=30,
        language="Korean",
        structure="Monologue",
        available_options=available_options,
    )

    if not gemini_client:
        logger.warning("[AnalyzeTopic] Gemini 클라이언트 미설정, 기본값 반환")
        return fallback

    template_vars = {
        "topic": topic,
        "description": description or "",
        "durations": SHORTS_DURATIONS,
        "languages": STORYBOARD_LANGUAGES,
        "structures": STRUCTURE_METADATA,
        "messages": messages or [],
    }

    try:
        from google.genai import types

        tmpl = template_env.get_template("creative/analyze_topic.j2")
        prompt = tmpl.render(**template_vars)
        config = types.GenerateContentConfig(safety_settings=GEMINI_SAFETY_SETTINGS)
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=config,
        )
        parsed = parse_json_response(response.text or "")
        logger.debug("[AnalyzeTopic] Gemini 응답: %s", {k: v for k, v in parsed.items() if k != "reasoning"})
    except Exception as e:
        logger.warning("[AnalyzeTopic] Gemini 호출/파싱 실패, 기본값 반환: %s", e)
        return fallback

    status = parsed.get("status", "recommend")
    resolved_topic = str(parsed.get("resolved_topic", "") or "").strip()[:50]
    questions = parsed.get("questions") or []
    if status == "clarify" and questions:
        return TopicAnalyzeResponse(
            status="clarify",
            resolved_topic=resolved_topic or topic,
            questions=questions,
            reasoning=parsed.get("reasoning", ""),
            available_options=available_options,
        )

    result = _validate_topic_analysis(parsed)
    return TopicAnalyzeResponse(
        status="recommend",
        resolved_topic=resolved_topic or topic,
        available_options=available_options,
        **result,
    )


def _validate_topic_analysis(parsed: dict) -> dict:
    """LLM 반환값을 검증하고, 유효하지 않은 값은 기본값으로 대체한다."""
    from config import SHORTS_DURATIONS, STORYBOARD_LANGUAGES
    from services.agent.inventory import STRUCTURE_METADATA

    structure_id_to_name = {s.id: s.name for s in STRUCTURE_METADATA}

    duration = parsed.get("duration", 30)
    if duration not in SHORTS_DURATIONS:
        duration = 30

    raw_structure = parsed.get("structure", "monologue")
    structure_key = raw_structure.lower() if isinstance(raw_structure, str) else "monologue"
    structure = structure_id_to_name.get(structure_key, "Monologue")

    language = parsed.get("language", "Korean")
    valid_languages = {lang["value"] for lang in STORYBOARD_LANGUAGES}
    if language not in valid_languages:
        language = "Korean"

    return {
        "duration": duration,
        "language": language,
        "structure": structure,
        "reasoning": parsed.get("reasoning", ""),
    }


def _build_options() -> AvailableOptions:
    """인라인 편집용 옵션 목록을 구성한다 (duration, language만 유의미)."""
    from config import SHORTS_DURATIONS, STORYBOARD_LANGUAGES
    from schemas import AvailableOptions

    return AvailableOptions(
        durations=SHORTS_DURATIONS,
        languages=STORYBOARD_LANGUAGES,
    )
