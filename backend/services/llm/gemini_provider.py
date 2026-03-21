"""GeminiProvider — Gemini SDK 래퍼. 429 retry + PROHIBITED fallback + trace 내장."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import config as _cfg
from config import (
    GEMINI_FALLBACK_MODEL,
    GEMINI_SAFETY_SETTINGS,
    GEMINI_TEXT_MODEL,
    GEMINI_TIMEOUT_MS,
    logger,
)
from services.agent.observability import _extract_usage, _safe_extract_text, trace_llm_call
from services.llm.types import LLMConfig, LLMResponse

# 429/5xx 지수 백오프 딜레이 (초)
_RETRY_DELAYS = [2, 8, 30]

# trace input에 system_instruction을 포함할 때의 최대 길이
_MAX_SYSTEM_LEN = 2000


def _get_client():
    """Gemini client를 반환. closed 시 재생성."""
    if _cfg.gemini_client is None:
        return None
    try:
        # httpx client closed 여부 — 내부 _client가 closed인지 확인
        http = getattr(_cfg.gemini_client, "_api_client", None)
        http = getattr(http, "_httpx_client", None)
        if http and getattr(http, "is_closed", False):
            raise RuntimeError("client closed")
    except (AttributeError, RuntimeError):
        from google import genai

        logger.info("[GeminiProvider] Client 재생성 (이전 client closed)")
        _cfg.gemini_client = genai.Client(api_key=_cfg.GEMINI_API_KEY)
    return _cfg.gemini_client


def _is_retryable(exc: Exception) -> bool:
    """429/5xx 또는 client closed 에러인지 확인한다."""
    msg = str(exc)
    if "client has been closed" in msg:
        return True
    return bool(re.search(r"429|5\d{2}", msg))


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
        *,
        metadata: dict[str, Any] | None = None,
        langfuse_prompt: Any = None,
    ) -> LLMResponse:
        """Gemini API를 호출하고 LLMResponse를 반환한다."""
        from google.genai import types

        if _get_client() is None:
            raise RuntimeError("Gemini client is not initialized. Check GEMINI_API_KEY in .env")

        resolved_model = model or GEMINI_TEXT_MODEL
        gemini_config = types.GenerateContentConfig(
            system_instruction=config.system_instruction,
            temperature=config.temperature,
            safety_settings=GEMINI_SAFETY_SETTINGS,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        )

        # trace input에 system_instruction 포함 (가시성 확보)
        trace_input = contents
        if config.system_instruction:
            sys_preview = config.system_instruction[:_MAX_SYSTEM_LEN]
            trace_input = f"[SYSTEM]\n{sys_preview}\n\n[USER]\n{contents}"

        # 429/5xx retry (지수 백오프: 2s, 8s, 30s)
        max_attempts = len(_RETRY_DELAYS) + 1
        response = None
        obs_id: str | None = None
        for attempt in range(max_attempts):
            try:
                async with trace_llm_call(
                    name=step_name,
                    model=resolved_model,
                    input_text=trace_input,
                    metadata=metadata,
                    langfuse_prompt=langfuse_prompt,
                ) as llm:
                    response = await _get_client().aio.models.generate_content(
                        model=resolved_model,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm.record(response)
                    obs_id = getattr(llm.generation, "id", None)
                break
            except Exception as exc:
                if attempt < len(_RETRY_DELAYS) and _is_retryable(exc):
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "[GeminiProvider] retry %d/%d after %ds: %s",
                        attempt + 1,
                        len(_RETRY_DELAYS),
                        delay,
                        str(exc)[:100],
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        # PROHIBITED_CONTENT fallback
        _text = _safe_extract_text(response) if response else ""
        if not _text:
            block_reason = _extract_block_reason(response) if response else None
            if block_reason and "PROHIBITED" in block_reason:
                logger.warning(
                    "[%s][Fallback] PROHIBITED_CONTENT → %s",
                    step_name,
                    GEMINI_FALLBACK_MODEL,
                )
                fb_metadata = {
                    **(metadata or {}),
                    "prohibited_fallback": True,
                    "fallback_model": GEMINI_FALLBACK_MODEL,
                }
                async with trace_llm_call(
                    name=step_name,
                    model=GEMINI_FALLBACK_MODEL,
                    input_text=trace_input,
                    metadata=fb_metadata,
                ) as llm_fb:
                    response = await _get_client().aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm_fb.record(response)
                    obs_id = getattr(llm_fb.generation, "id", None)

        return LLMResponse(
            text=_safe_extract_text(response) if response else "",
            usage=_extract_usage(response) if response else None,
            raw=response,
            observation_id=obs_id,
        )

    async def generate_with_tools(
        self,
        step_name: str,
        contents: list,
        config: LLMConfig,
        tools: list,
        model: str | None = None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Function Calling 전용 (tools/base.py에서 사용). Protocol 외부 확장."""
        from google.genai import types

        if _get_client() is None:
            raise RuntimeError("Gemini client is not initialized. Check GEMINI_API_KEY in .env")

        resolved_model = model or GEMINI_TEXT_MODEL
        gemini_config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=config.system_instruction,
            temperature=config.temperature,
            safety_settings=GEMINI_SAFETY_SETTINGS,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        )

        # 429/5xx retry (지수 백오프: 2s, 8s, 30s)
        max_attempts = len(_RETRY_DELAYS) + 1
        response = None
        obs_id: str | None = None
        for attempt in range(max_attempts):
            try:
                async with trace_llm_call(
                    name=step_name,
                    model=resolved_model,
                    input_text=str(contents)[:1000],
                    metadata=metadata,
                ) as llm:
                    response = await _get_client().aio.models.generate_content(
                        model=resolved_model,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm.record(response)
                    obs_id = getattr(llm.generation, "id", None)
                break
            except Exception as exc:
                if attempt < len(_RETRY_DELAYS) and _is_retryable(exc):
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "[GeminiProvider.tools] retry %d/%d after %ds: %s",
                        attempt + 1,
                        len(_RETRY_DELAYS),
                        delay,
                        str(exc)[:100],
                    )
                    await asyncio.sleep(delay)
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
                fb_metadata = {
                    **(metadata or {}),
                    "prohibited_fallback": True,
                    "fallback_model": GEMINI_FALLBACK_MODEL,
                }
                async with trace_llm_call(
                    name=step_name,
                    model=GEMINI_FALLBACK_MODEL,
                    input_text=str(contents)[:1000],
                    metadata=fb_metadata,
                ) as llm_fb:
                    response = await _get_client().aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=contents,
                        config=gemini_config,
                    )
                    llm_fb.record(response)
                    obs_id = getattr(llm_fb.generation, "id", None)

        return LLMResponse(
            text=_safe_extract_text(response) if response else "",
            usage=_extract_usage(response) if response else None,
            raw=response,
            observation_id=obs_id,
        )
