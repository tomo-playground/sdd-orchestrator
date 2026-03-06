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
    group_id: int | None,
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
    from services.agent.inventory import STRUCTURE_METADATA, load_full_inventory
    from services.creative_utils import parse_json_response

    inventory = load_full_inventory(group_id)
    characters = inventory.get("characters", [])

    # 캐릭터가 비었으면 전체 활성 캐릭터를 폴백 로드 (추천용)
    # group_id가 있어도 해당 그룹에 캐릭터가 없을 수 있음
    if not characters:
        characters = _load_all_characters()

    logger.debug(
        "[AnalyzeTopic] group_id=%s, characters=%s",
        group_id,
        [(c.id, c.name) for c in characters],
    )

    # 인라인 편집용 옵션 목록 구성 (fallback 포함 항상 반환)
    available_options = _build_options(group_id, characters)
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
        "characters": characters,
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
        # 구 키 → 신 키 폴백 (LLM이 이전 포맷으로 응답할 경우 대비)
        if "character_id" in parsed and "character_a_id" not in parsed:
            parsed["character_a_id"] = parsed.pop("character_id")
        if "character_name" in parsed and "character_a_name" not in parsed:
            parsed["character_a_name"] = parsed.pop("character_name")
        logger.debug(
            "[AnalyzeTopic] Gemini 응답: character_a_id=%s, character_b_id=%s, valid_chars=%s",
            parsed.get("character_a_id"),
            parsed.get("character_b_id"),
            [c.id for c in characters],
        )
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

    result = _validate_topic_analysis(parsed, characters)
    return TopicAnalyzeResponse(
        status="recommend",
        resolved_topic=resolved_topic or topic,
        available_options=available_options,
        **result,
    )


def _validate_character(parsed: dict, key: str, valid_char_map: dict) -> tuple[int | None, str | None]:
    """캐릭터 ID/Name 쌍을 검증한다. 유효하지 않으면 (None, None) 반환."""
    raw = parsed.get(key)
    if raw is None:
        return None, None
    try:
        char_id = int(raw)
    except (TypeError, ValueError):
        return None, None
    if char_id <= 0:
        return None, None
    if char_id in valid_char_map:
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

    character_a_id, character_a_name = _validate_character(parsed, "character_a_id", valid_char_map)
    character_b_id, character_b_name = _validate_character(parsed, "character_b_id", valid_char_map)

    return {
        "duration": duration,
        "language": language,
        "structure": structure,
        "character_a_id": character_a_id,
        "character_a_name": character_a_name,
        "character_b_id": character_b_id,
        "character_b_name": character_b_name,
        "reasoning": parsed.get("reasoning", ""),
    }


def _build_options(group_id: int | None, characters: list) -> AvailableOptions:
    """인라인 편집용 옵션 목록을 구성한다 (DB 세션 불필요)."""
    from config import SHORTS_DURATIONS, STORYBOARD_LANGUAGES
    from schemas import AvailableOptions
    from services.presets import PRESETS

    structures = [{"value": p.structure, "label": p.name_ko} for p in PRESETS.values()]
    char_list = [{"id": c.id, "name": c.name} for c in characters]

    return AvailableOptions(
        durations=SHORTS_DURATIONS,
        structures=structures,
        languages=STORYBOARD_LANGUAGES,
        characters=char_list,
    )


def _load_all_characters() -> list:
    """group_id 없이 전체 활성 캐릭터를 로드한다 (추천 전용)."""
    from database import get_db_session
    from services.agent.inventory import _build_character_summary

    try:
        from models.character import Character

        with get_db_session() as db:
            rows = db.query(Character).filter(Character.deleted_at.is_(None)).order_by(Character.name).limit(20).all()
            return [_build_character_summary(c, 0) for c in rows]  # 0 = no score (추천 전용)
    except Exception as e:
        logger.warning("[AnalyzeTopic] 전체 캐릭터 로드 실패: %s", e)
        return []
