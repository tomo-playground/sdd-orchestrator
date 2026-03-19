"""Topic analysis service — Gemini 기반 토픽 분석 및 설정 추천."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import logger
from schemas import TopicAnalyzeResponse

if TYPE_CHECKING:
    from schemas import AvailableOptions


async def analyze_topic(
    topic: str,
    description: str | None,
    group_id: int | None,  # noqa: ARG001 — 라우터 시그니처 유지
    messages: list[dict] | None = None,
    storyboard_id: int | None = None,
) -> TopicAnalyzeResponse:
    """토픽을 분석하여 최적의 영상 설정을 추천한다.

    대화 이력(messages)이 있으면 맥락을 유지하며,
    정보가 부족하면 clarify 질문을 반환한다.
    """
    from config import (
        DEFAULT_LANGUAGE,
        DEFAULT_STRUCTURE,
        GEMINI_SAFETY_SETTINGS,
        GEMINI_TEXT_MODEL,
        SHORTS_DURATIONS,
        STORYBOARD_LANGUAGES,
        STRUCTURE_METADATA,
        gemini_client,
    )
    from services.creative_utils import parse_json_response

    # 인라인 편집용 옵션 목록 구성 (캐릭터/구성은 Director SSOT → 여기서 불필요)
    available_options = _build_options()
    fallback = TopicAnalyzeResponse(
        duration=30,
        language=DEFAULT_LANGUAGE,
        structure=DEFAULT_STRUCTURE,
        available_options=available_options,
    )

    if not gemini_client:
        logger.warning("[AnalyzeTopic] Gemini 클라이언트 미설정, 기본값 반환")
        return fallback

    from services.agent.langfuse_prompt import compile_prompt
    from services.agent.prompt_builders_c import (
        build_description_section,
        build_durations_list,
        build_languages_list,
        build_messages_block,
        build_structures_list,
    )

    template_vars = {
        "topic": topic,
        "description_section": build_description_section(description),
        "messages_block": build_messages_block(messages),
        "durations_list": build_durations_list(SHORTS_DURATIONS),
        "languages_list": build_languages_list(STORYBOARD_LANGUAGES),
        "structures_list": build_structures_list(STRUCTURE_METADATA),
    }

    try:
        from google.genai import types

        from services.agent.observability import trace_context, trace_llm_call

        session_id = f"storyboard-{storyboard_id}" if storyboard_id else None
        compiled = compile_prompt("creative/analyze_topic", **template_vars)
        prompt = compiled.user
        sys_instruction = compiled.system or ""
        config = types.GenerateContentConfig(
            safety_settings=GEMINI_SAFETY_SETTINGS,
            system_instruction=sys_instruction if sys_instruction else None,
        )

        async with trace_context("topic.analyze", session_id=session_id, input_data={"topic": topic}):
            async with trace_llm_call(
                "generate_content analyze_topic",
                model=GEMINI_TEXT_MODEL,
                input_text=prompt[:2000],
                metadata={"template": "creative/analyze_topic"},
                langfuse_prompt=compiled.langfuse_prompt,
            ) as llm:
                response = await gemini_client.aio.models.generate_content(
                    model=GEMINI_TEXT_MODEL,
                    contents=prompt,
                    config=config,
                )
                llm.record(response)

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
    from config import (
        DEFAULT_STRUCTURE,
        SHORTS_DURATIONS,
        STRUCTURE_IDS,
        coerce_language_id,
        coerce_structure_id,
    )

    duration = parsed.get("duration", 30)
    if duration not in SHORTS_DURATIONS:
        duration = 30

    structure = coerce_structure_id(parsed.get("structure"))
    if structure not in STRUCTURE_IDS:
        structure = DEFAULT_STRUCTURE

    language = coerce_language_id(parsed.get("language"))

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
