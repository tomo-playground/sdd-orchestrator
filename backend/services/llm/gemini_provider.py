"""GeminiProvider — Gemini SDK 래퍼. 429 retry + PROHIBITED fallback + trace 내장."""
from __future__ import annotations

import asyncio
import re
from typing import Any

from config import (
    GEMINI_FALLBACK_MODEL,
    GEMINI_SAFETY_SETTINGS,
    GEMINI_TEXT_MODEL,
    gemini_client,
    logger,
)
from services.agent.observability import _extract_usage, trace_llm_call
from services.llm.types import LLMConfig, LLMResponse


def _is_retryable(exc: Exception) -> bool:
    """429/5xx 에러인지 확인한다."""
    return bool(re.search(r"429|5\d{2}", str(exc)))


def _extract_block_reason(response: Any) -> str | None:
    """Gemini 응답에서 차단 사유를 추출한다. 정상 종료(STOP)는 무시."""
    if getattr(response, "prompt_feedback", None) and response.prompt_feedback.block_reason:
        return str(response.prompt_feedback.block_reason)
    if getattr(response, "candidates", None):
        for candidate in response.candidates:
            reason = str(candidate.finish_reason) if candidate.finish_reason else None
            if reason and reason != "STOP":
                return reason
    return None


class GeminiProvider:
    """Gemini SDK 래퍼. 429 retry + PROHIBITED fallback + trace 내장."""

    async def generate(
        self,
        step_name: str,
        contents: str,
        config: LLMConfig,
        model: str | None = None,
    ) -> LLMResponse:
        """Gemini API를 호출하고 LLMResponse를 반환한다."""
        from google.genai import types

        if gemini_client is None:
            raise RuntimeError("Gemini client is not initialized. Check GEMINI_API_KEY in .env")

        resolved_model = model or GEMINI_TEXT_MODEL
        gemini_config = types.GenerateContentConfig(
            system_instruction=config.system_instruction,
            temperature=config.temperature,
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )

        # 429/5xx retry
        delays = [1, 3]
        response = None
        for attempt in range(3):
            try:
                async with trace_llm_call(
                    name=step_name,
                    model=resolved_model,
                    input_text=contents,
                ) as llm:
                    response = await gemini_client.aio.models.generate_content(
                        model=resolved_model,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm.record(response)
                break
            except Exception as exc:
                if attempt < 2 and _is_retryable(exc):
                    logger.warning(
                        "[GeminiProvider] retry %d/2 after %ds: %s",
                        attempt + 1,
                        delays[attempt],
                        str(exc)[:100],
                    )
                    await asyncio.sleep(delays[attempt])
                else:
                    raise

        # PROHIBITED_CONTENT fallback
        if not (response.text if response else None):
            block_reason = _extract_block_reason(response) if response else None
            if block_reason and "PROHIBITED" in block_reason:
                logger.warning(
                    "[%s][Fallback] PROHIBITED_CONTENT → %s",
                    step_name,
                    GEMINI_FALLBACK_MODEL,
                )
                async with trace_llm_call(
                    name=f"{step_name}_fallback",
                    model=GEMINI_FALLBACK_MODEL,
                    input_text=contents,
                ) as llm_fb:
                    response = await gemini_client.aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm_fb.record(response)

        return LLMResponse(
            text=(response.text or "") if response else "",
            usage=_extract_usage(response) if response else None,
            raw=response,
        )

    async def generate_with_tools(
        self,
        step_name: str,
        contents: list,
        config: LLMConfig,
        tools: list,
        model: str | None = None,
    ) -> LLMResponse:
        """Function Calling 전용 (tools/base.py에서 사용). Protocol 외부 확장."""
        from google.genai import types

        if gemini_client is None:
            raise RuntimeError("Gemini client is not initialized. Check GEMINI_API_KEY in .env")

        resolved_model = model or GEMINI_TEXT_MODEL
        gemini_config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=config.system_instruction,
            temperature=config.temperature,
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )

        # 429/5xx retry
        delays = [1, 3]
        response = None
        for attempt in range(3):
            try:
                async with trace_llm_call(
                    name=step_name,
                    model=resolved_model,
                    input_text=str(contents)[:1000],
                ) as llm:
                    response = await gemini_client.aio.models.generate_content(
                        model=resolved_model,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm.record(response)
                break
            except Exception as exc:
                if attempt < 2 and _is_retryable(exc):
                    logger.warning(
                        "[GeminiProvider.tools] retry %d/2 after %ds: %s",
                        attempt + 1,
                        delays[attempt],
                        str(exc)[:100],
                    )
                    await asyncio.sleep(delays[attempt])
                else:
                    raise

        # PROHIBITED_CONTENT fallback
        if response and not response.candidates:
            block_reason = _extract_block_reason(response)
            if block_reason and "PROHIBITED" in block_reason:
                logger.warning(
                    "[%s][Fallback] PROHIBITED_CONTENT → %s",
                    step_name,
                    GEMINI_FALLBACK_MODEL,
                )
                async with trace_llm_call(
                    name=f"{step_name}_fallback",
                    model=GEMINI_FALLBACK_MODEL,
                    input_text=str(contents)[:1000],
                ) as llm_fb:
                    response = await gemini_client.aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm_fb.record(response)

        return LLMResponse(
            text=(response.text or "") if response else "",
            usage=_extract_usage(response) if response else None,
            raw=response,
        )


