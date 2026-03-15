"""Gemini Function Calling 인프라 (Phase 10-B-1).

Tool 정의, 실행, 로깅을 위한 핵심 유틸리티.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any, TypedDict

from google.genai import types

from config import logger
from services.llm import LLMConfig, get_llm_provider
from services.llm.gemini_provider import GeminiProvider


class ToolCallLog(TypedDict):
    """도구 호출 기록."""

    tool_name: str
    arguments: dict[str, Any]
    result: Any
    error: str | None


def _is_likely_structured_output(text: str) -> bool:
    """텍스트가 JSON 등 구조화된 출력일 가능성이 있는지 판별한다."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped[0] in ("{", "["):
        return True
    if "```" in stripped:
        return True
    if "{" in stripped and "}" in stripped:
        return True
    return False


def define_tool(
    name: str,
    description: str,
    parameters: dict[str, dict[str, Any]],
    required: list[str] | None = None,
) -> types.Tool:
    """Gemini Function Calling용 도구 정의.

    Args:
        name: 도구 이름 (snake_case)
        description: 도구 설명 (LLM이 선택 판단에 사용)
        parameters: 파라미터 스키마 (name → {type, description})
        required: 필수 파라미터 목록

    Returns:
        Gemini Tool 객체

    Example:
        >>> tool = define_tool(
        ...     name="search_history",
        ...     description="과거 생성 이력 검색",
        ...     parameters={
        ...         "topic": {"type": "string", "description": "검색 주제"},
        ...         "limit": {"type": "integer", "description": "결과 개수"},
        ...     },
        ...     required=["topic"],
        ... )
    """
    # Schema 속성 매핑
    properties: dict[str, types.Schema] = {}
    for param_name, param_def in parameters.items():
        schema_type = param_def.get("type", "string").upper()  # STRING, INTEGER, etc.
        properties[param_name] = types.Schema(
            type=getattr(types.Type, schema_type, types.Type.STRING),
            description=param_def.get("description", ""),
        )

    function_declaration = types.FunctionDeclaration(
        name=name,
        description=description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties=properties,
            required=required or [],
        ),
    )

    return types.Tool(function_declarations=[function_declaration])


async def call_with_tools(
    prompt: str,
    tools: list[types.Tool],
    tool_executors: dict[str, Callable],
    max_calls: int | None = None,
    trace_name: str = "tool_calling",
    temperature: float = 0.7,
    system_instruction: str | None = None,
) -> tuple[str, list[ToolCallLog]]:
    """Gemini Function Calling 루프 실행.

    LLM이 도구를 선택적으로 호출하는 ReAct 루프:
    1. LLM 호출 → tool_call 감지
    2. 도구 실행
    3. 결과를 LLM에 재주입
    4. 최종 응답까지 반복 (최대 max_calls)

    Args:
        prompt: 초기 프롬프트
        tools: 사용 가능한 도구 목록
        tool_executors: 도구 이름 → 실행 함수 매핑
        max_calls: 최대 도구 호출 횟수 (비용 가드레일)
        trace_name: LangFuse 트레이스 이름
        temperature: Gemini 생성 온도 (기본 0.7)

    Returns:
        (최종 LLM 응답, 도구 호출 로그). max_calls 도달 시에도 누적 텍스트를 반환.
        텍스트가 비어있고 도구 호출이 있었으면, 도구 없이 1회 추가 호출(fallback)을 시도한다.
    """
    if max_calls is None:
        from config_pipelines import MAX_TOOL_CALLS_PER_NODE as default_max

        max_calls = default_max

    provider: GeminiProvider = get_llm_provider()  # type: ignore[assignment]
    llm_config = LLMConfig(temperature=temperature, system_instruction=system_instruction)

    tool_logs: list[ToolCallLog] = []
    # 첫 메시지는 문자열로 전달
    contents: list[str | types.Content] = [prompt]
    call_count = 0
    # 매 스텝의 텍스트 파트를 누적 (function_call 혼재 응답에서도 보존)
    accumulated_text: list[str] = []

    while call_count < max_calls:
        # GeminiProvider를 통해 Function Calling 호출 (trace + PROHIBITED fallback 내장)
        llm_response = await provider.generate_with_tools(
            step_name=f"{trace_name}_step_{call_count + 1}",
            contents=contents,  # type: ignore[arg-type]
            config=llm_config,
            tools=tools,  # type: ignore[arg-type]
        )
        response = llm_response.raw

        # Tool call 감지
        if not response.candidates:
            block_reason = getattr(getattr(response, "prompt_feedback", None), "block_reason", None)
            logger.warning("[Tool-Calling] No candidates in response (block_reason=%s)", block_reason)
            break

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            logger.warning("[Tool-Calling] No valid response from Gemini")
            break

        parts = candidate.content.parts
        has_tool_call = any(hasattr(part, "function_call") and part.function_call for part in parts)

        # 텍스트 파트 수집 (function_call과 혼재해도 보존)
        step_text = "".join(part.text for part in parts if hasattr(part, "text") and part.text)
        if step_text:
            accumulated_text.append(step_text)

        if not has_tool_call:
            final_text = "\n".join(accumulated_text).strip()
            if final_text:
                logger.info("[Tool-Calling] Final response received (no tool calls)")
                return final_text, tool_logs
            # 텍스트가 비어있으면 fallback으로 진행
            logger.warning("[Tool-Calling] Final response has empty text, falling through to fallback")
            break

        # 도구 실행
        function_responses: list[types.Part] = []
        for part in parts:
            if not (hasattr(part, "function_call") and part.function_call):
                continue

            function_call = part.function_call
            tool_name = function_call.name or "unknown"
            arguments = dict(function_call.args) if function_call.args else {}

            logger.info("[Tool-Calling] Executing tool: %s(%s)", tool_name, json.dumps(arguments, ensure_ascii=False))

            # 도구 실행
            executor = tool_executors.get(tool_name) if tool_name else None
            if not executor:
                error_msg = f"Tool '{tool_name}' not found in executors"
                logger.error("[Tool-Calling] %s", error_msg)
                tool_logs.append(
                    ToolCallLog(
                        tool_name=tool_name or "unknown",
                        arguments=arguments,
                        result=None,
                        error=error_msg,
                    )
                )
                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name or "unknown",
                            response={"error": error_msg},
                        )
                    )
                )
                continue

            try:
                # 비동기 함수 실행
                if asyncio.iscoroutinefunction(executor):
                    result = await executor(**arguments)
                else:
                    result = executor(**arguments)

                logger.info("[Tool-Calling] Tool '%s' result: %s", tool_name, str(result)[:200])

                tool_logs.append(
                    ToolCallLog(
                        tool_name=tool_name or "unknown",
                        arguments=arguments,
                        result=result,
                        error=None,
                    )
                )

                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name or "unknown",
                            response={"result": result},
                        )
                    )
                )

            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                logger.error("[Tool-Calling] Tool '%s' failed: %s", tool_name, error_msg)

                tool_logs.append(
                    ToolCallLog(
                        tool_name=tool_name or "unknown",
                        arguments=arguments,
                        result=None,
                        error=error_msg,
                    )
                )

                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name or "unknown",
                            response={"error": error_msg},
                        )
                    )
                )

        # 도구 응답을 컨텍스트에 추가
        if candidate.content:
            contents.append(candidate.content)  # type: ignore[arg-type]
        contents.append(types.Content(parts=function_responses))

        call_count += 1

    # max_calls 도달 또는 break — 누적 텍스트가 있으면 반환
    if call_count >= max_calls:
        logger.warning(
            "[Tool-Calling] Max tool calls (%d) reached, returning accumulated text (%d chars)",
            max_calls,
            len("".join(accumulated_text)),
        )

    final = "\n".join(accumulated_text).strip()

    # 누적 텍스트가 자연어(비구조화)이면 fallback 대상으로 전환
    if final and not _is_likely_structured_output(final):
        logger.warning(
            "[Tool-Calling] 누적 텍스트가 비구조화 자연어로 보임 (%d chars, 앞 80자=%r), fallback 시도",
            len(final),
            final[:80],
        )
        final = ""

    # Fallback: 텍스트가 비면, 도구 없이 재호출하여 텍스트 응답 강제
    if not final:
        logger.info(
            "[Tool-Calling] No text response (tool_calls=%d), fallback call without tools",
            len(tool_logs),
        )
        try:
            # 도구 없이 새 요청: 원본 프롬프트 + JSON 강제 지시
            fallback_instruction = (
                "도구를 사용했지만 최종 JSON 응답을 제공하지 않았습니다. "
                "대화 중 도구 결과를 바탕으로 지금 최종 답변을 유효한 JSON으로만 작성하세요. "
                "설명, markdown 코드블록, 서문 없이 순수 JSON만 출력하세요."
            )
            # contents에 이미 도구 결과가 포함되어 있으므로 그대로 활용
            fallback_contents: list[Any] = list(contents)
            fallback_contents.append(fallback_instruction)

            fallback_resp = await provider.generate_with_tools(
                step_name=f"{trace_name}_fallback",
                contents=fallback_contents,  # type: ignore[arg-type]
                config=LLMConfig(temperature=temperature, system_instruction=system_instruction),
                tools=[],
            )
            raw_fb = fallback_resp.raw
            if raw_fb and raw_fb.candidates and raw_fb.candidates[0].content:
                fb_parts = raw_fb.candidates[0].content.parts or []
                final = "\n".join(p.text for p in fb_parts if hasattr(p, "text") and p.text).strip()
                logger.info("[Tool-Calling] Fallback produced %d chars", len(final))
        except Exception as e:
            logger.warning("[Tool-Calling] Fallback call failed: %s", e)

    return final, tool_logs


async def call_direct(
    prompt: str,
    trace_name: str = "direct_call",
    temperature: float = 0.0,
    system_instruction: str | None = None,
) -> str:
    """도구 없이 LLM을 직접 호출한다. JSON 강제 재시도 등에 사용."""
    provider = get_llm_provider()
    llm_response = await provider.generate(
        step_name=trace_name,
        contents=prompt,
        config=LLMConfig(temperature=temperature, system_instruction=system_instruction),
    )
    return llm_response.text
