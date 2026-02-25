"""Gemini Flash LLM 기반 태그 분류.

미분류 태그를 배치로 Gemini Flash에 전송하여 group_name을 추론한다.
모든 에러는 non-fatal — 실패 시 빈 리스트 반환 (기존 동작 유지).
"""

from __future__ import annotations

import json
from typing import TypedDict

from google.genai.types import GenerateContentConfig, HttpOptions

from config import GEMINI_CLASSIFIER_MODEL, GEMINI_CLASSIFIER_TIMEOUT_MS, gemini_client, logger
from services.keywords.patterns import GROUP_NAME_TO_LAYER

_VALID_GROUPS = frozenset(GROUP_NAME_TO_LAYER.keys())

# 대표 태그 예시 (프롬프트에 포함)
_GROUP_EXAMPLES: dict[str, str] = {
    "quality": "masterpiece, best_quality, absurdres",
    "subject": "1girl, solo, couple",
    "identity": "male, female",
    "hair_color": "black_hair, blonde_hair",
    "hair_length": "long_hair, short_hair",
    "hair_style": "ponytail, braid, bob_cut",
    "hair_accessory": "hairclip, headband, tiara",
    "eye_color": "blue_eyes, red_eyes",
    "skin_color": "pale_skin, dark_skin",
    "body_feature": "pointy_ears, wings, tail",
    "appearance": "freckles, tattoo, makeup",
    "body_type": "slim, petite, muscular, tall",
    "clothing": "shirt, skirt, uniform, glasses",
    "expression": "smile, crying, angry, surprised",
    "gaze": "looking_at_viewer, looking_away, eyes_closed",
    "pose": "standing, sitting, arms_crossed",
    "action": "walking, running, holding_phone, eating",
    "camera": "close-up, cowboy_shot, from_above, bokeh",
    "location_indoor_general": "indoors",
    "location_indoor_specific": "bedroom, classroom, cafe",
    "location_outdoor": "outdoors, street, forest, beach",
    "environment": "desk, window, computer, monitor, lamp",
    "background_type": "simple_background, blurry_background",
    "time_weather": "night, sunset, rainy, cherry_blossoms",
    "lighting": "cinematic_lighting, rim_light, neon",
    "mood": "romantic, melancholic, mysterious, cozy",
    "style": "anime, realistic, watercolor, chibi",
}


class LLMClassificationResult(TypedDict):
    tag: str
    group_name: str
    confidence: float


def _build_prompt(tags: list[str]) -> str:
    """GROUP_NAME_TO_LAYER 기반 분류 프롬프트 생성."""
    group_lines = "\n".join(f"  - {group}: {_GROUP_EXAMPLES.get(group, '')}" for group in sorted(_VALID_GROUPS))
    tag_list = json.dumps(tags, ensure_ascii=False)

    return f"""You are a Danbooru/Stable Diffusion tag classifier.

Classify each tag into exactly one group_name from the list below.
Consider the OVERALL meaning of compound tags (e.g. "computer_monitor" = environment, "cinematic_shadows" = lighting).

Available group_names and examples:
{group_lines}

Tags to classify:
{tag_list}

Respond ONLY with a JSON array. No explanation.
Format: [{{"tag": "...", "group_name": "...", "confidence": 0.0-1.0}}]"""


def _validate_results(
    raw: list[dict],
    valid_groups: frozenset[str],
) -> list[LLMClassificationResult]:
    """group_name 유효성 검증 + confidence 클램프."""
    validated: list[LLMClassificationResult] = []
    for item in raw:
        tag = item.get("tag")
        group = item.get("group_name")
        conf = item.get("confidence", 0.7)
        if not tag or not group or group not in valid_groups:
            continue
        validated.append(
            {
                "tag": str(tag),
                "group_name": str(group),
                "confidence": max(0.0, min(1.0, float(conf))),
            }
        )
    return validated


def _parse_llm_json(text: str) -> list[dict]:
    """LLM 응답에서 JSON 배열을 추출한다. 코드블록/preamble 제거."""
    import re

    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    parsed = json.loads(cleaned)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and "results" in parsed:
        return parsed["results"]
    return [parsed] if isinstance(parsed, dict) else []


async def classify_tags_via_llm(tags: list[str]) -> list[LLMClassificationResult]:
    """미분류 태그를 배치로 Gemini Flash에 전송하여 group_name 추론."""
    if not tags:
        return []
    if not gemini_client:
        logger.warning("[TagClassifier LLM] gemini_client is None, skipping")
        return []

    prompt = _build_prompt(tags)
    try:
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_CLASSIFIER_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                http_options=HttpOptions(timeout=GEMINI_CLASSIFIER_TIMEOUT_MS),
            ),
        )
        text = response.text or ""
        results = _parse_llm_json(text)

        validated = _validate_results(results, _VALID_GROUPS)
        logger.info(
            "[TagClassifier LLM] %d/%d tags classified via Gemini Flash",
            len(validated),
            len(tags),
        )
        return validated
    except Exception:
        logger.warning("[TagClassifier LLM] Gemini API call failed", exc_info=True)
        return []
