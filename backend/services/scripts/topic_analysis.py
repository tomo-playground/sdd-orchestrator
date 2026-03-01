"""Topic analysis service — Gemini 기반 토픽 분석 및 설정 추천."""

from __future__ import annotations

from config import logger
from schemas import TopicAnalyzeResponse


async def analyze_topic(
    topic: str,
    description: str | None,
    group_id: int | None,
    messages: list[dict] | None = None,
) -> TopicAnalyzeResponse:
    """토픽을 분석하여 최적의 영상 설정을 추천한다.

    대화 이력(messages)이 있으면 맥락을 유지하며,
    정보가 부족하면 clarify 질문을 반환한다.
    """
    from config import GEMINI_TEXT_MODEL, SHORTS_DURATIONS, STORYBOARD_LANGUAGES, gemini_client, template_env
    from services.agent.inventory import STRUCTURE_METADATA, load_full_inventory
    from services.creative_utils import parse_json_response

    fallback = TopicAnalyzeResponse(duration=30, language="Korean", structure="Monologue")

    if not gemini_client:
        logger.warning("[AnalyzeTopic] Gemini 클라이언트 미설정, 기본값 반환")
        return fallback

    inventory = load_full_inventory(group_id)
    characters = inventory.get("characters", [])

    template_vars = {
        "topic": topic,
        "description": description or "",
        "durations": SHORTS_DURATIONS,
        "languages": STORYBOARD_LANGUAGES,
        "structures": STRUCTURE_METADATA,
        "characters": characters,
        "messages": messages or [],
    }

    try:
        tmpl = template_env.get_template("creative/analyze_topic.j2")
        prompt = tmpl.render(**template_vars)
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        parsed = parse_json_response(response.text or "")
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
        )

    result = _validate_topic_analysis(parsed, characters)
    return TopicAnalyzeResponse(
        status="recommend",
        resolved_topic=resolved_topic or topic,
        **result,
    )


def _validate_character(parsed: dict, key: str, valid_char_map: dict) -> tuple[int | None, str | None]:
    """캐릭터 ID/Name 쌍을 검증한다. 유효하지 않으면 (None, None) 반환."""
    char_id = parsed.get(key)
    if char_id and char_id in valid_char_map:
        return char_id, valid_char_map[char_id]
    return None, None


def _validate_topic_analysis(parsed: dict, characters: list) -> dict:
    """LLM 반환값을 검증하고, 유효하지 않은 값은 기본값으로 대체한다."""
    from config import SHORTS_DURATIONS, STORYBOARD_LANGUAGES
    from services.agent.inventory import STRUCTURE_METADATA

    structure_id_to_name = {s.id: s.name for s in STRUCTURE_METADATA}
    valid_char_map = {c.id: c.name for c in characters}

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

    character_id, character_name = _validate_character(parsed, "character_id", valid_char_map)
    character_b_id, character_b_name = _validate_character(parsed, "character_b_id", valid_char_map)

    return {
        "duration": duration,
        "language": language,
        "structure": structure,
        "character_id": character_id,
        "character_name": character_name,
        "character_b_id": character_b_id,
        "character_b_name": character_b_name,
        "reasoning": parsed.get("reasoning", ""),
    }
