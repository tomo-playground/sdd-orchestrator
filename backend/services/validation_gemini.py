"""Gemini Vision 기반 태그 평가 엔진.

validation.py에서 분리: evaluate_tags_with_gemini + 관련 헬퍼.
CLAUDE.md 필수 규칙 준수:
  - system_instruction → GenerateContentConfig.system_instruction
  - GEMINI_SAFETY_SETTINGS 적용
  - PROHIBITED_CONTENT 폴백 (GEMINI_FALLBACK_MODEL로 1회 재시도)
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any

from config import (
    GEMINI_FALLBACK_MODEL,
    GEMINI_SAFETY_SETTINGS,
    GEMINI_TEXT_MODEL,
    GEMINI_VISION_EVAL_TIMEOUT_S,
    gemini_client,
    logger,
)

_GEMINI_EVAL_SYSTEM = "You are an image analysis expert specializing in anime/illustration art."


def _extract_gemini_block_reason(response: Any) -> str | None:
    """Extract block reason from a Gemini response (STOP is ignored)."""
    if getattr(response, "prompt_feedback", None) and response.prompt_feedback.block_reason:
        return str(response.prompt_feedback.block_reason)
    if getattr(response, "candidates", None):
        for candidate in response.candidates:
            reason = str(candidate.finish_reason) if candidate.finish_reason else None
            if reason and reason != "STOP":
                return reason
    return None


def _parse_gemini_json_array(text: str) -> list[dict]:
    """Extract a JSON array from Gemini response text.

    Handles markdown code fences and bare arrays.
    Returns an empty list if parsing fails.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = cleaned.rstrip("`").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*]", cleaned, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            return []

    if not isinstance(parsed, list):
        return []

    return [item for item in parsed if isinstance(item, dict) and "tag" in item and "present" in item]


async def evaluate_tags_with_gemini(
    image_b64: str,
    tags: list[str],
) -> list[dict]:
    """Gemini Vision으로 비-WD14 태그를 평가한다.

    카메라, 조명, 분위기, 위치 등 WD14가 감지하지 못하는 태그를
    Gemini 멀티모달 API로 평가한다.

    Args:
        image_b64: Base64-encoded image (data URL prefix 없이).
        tags: 평가할 Danbooru 태그 목록.

    Returns:
        ``[{"tag": str, "present": bool, "confidence": float}]``
        실패 시 빈 리스트 반환 (graceful degradation).
    """
    if not tags:
        return []

    if gemini_client is None:
        logger.warning("[MatchRate] Gemini client not initialized, skipping vision eval")
        return []

    from google.genai import types

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        logger.warning("[MatchRate] Invalid base64 image, skipping vision eval")
        return []

    from services.agent.langfuse_prompt import compile_prompt
    from services.agent.prompt_builders import build_tags_block

    compiled = compile_prompt("validate_image_tags", tags_block=build_tags_block(tags))
    user_prompt = compiled.user

    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        user_prompt,
    ]
    gemini_config = types.GenerateContentConfig(
        system_instruction=_GEMINI_EVAL_SYSTEM,
        temperature=0.1,
        safety_settings=GEMINI_SAFETY_SETTINGS,
    )

    try:
        response = await asyncio.wait_for(
            gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=contents,
                config=gemini_config,
            ),
            timeout=GEMINI_VISION_EVAL_TIMEOUT_S,
        )
    except TimeoutError:
        logger.warning("[MatchRate] Gemini vision timed out after %ds", GEMINI_VISION_EVAL_TIMEOUT_S)
        return []
    except Exception as exc:
        logger.warning("[MatchRate] Gemini evaluation failed: %s", exc)
        return []

    raw_text = (response.text or "") if response else ""

    # PROHIBITED_CONTENT 폴백 (CLAUDE.md 규칙)
    if not raw_text:
        block_reason = _extract_gemini_block_reason(response) if response else None
        if block_reason and "PROHIBITED" in block_reason:
            logger.warning(
                "[MatchRate][Fallback] PROHIBITED_CONTENT → %s",
                GEMINI_FALLBACK_MODEL,
            )
            try:
                response = await asyncio.wait_for(
                    gemini_client.aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=contents,
                        config=gemini_config,
                    ),
                    timeout=GEMINI_VISION_EVAL_TIMEOUT_S,
                )
                raw_text = (response.text or "") if response else ""
            except Exception as fb_exc:
                logger.warning("[MatchRate] Fallback also failed: %s", fb_exc)
                return []

    if not raw_text:
        logger.warning("[MatchRate] Gemini returned empty response")
        return []

    results = _parse_gemini_json_array(raw_text)
    if not results:
        logger.warning("[MatchRate] Failed to parse Gemini JSON: %.200s", raw_text)
        return []

    return results
