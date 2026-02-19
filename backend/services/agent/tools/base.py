"""Gemini Function Calling 인프라 (Phase 10-B-1).

Tool 정의, 실행, 로깅을 위한 핵심 유틸리티.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any, TypedDict

from google.genai import types

from config import GEMINI_TEXT_MODEL, gemini_client, logger
from services.agent.observability import trace_llm_call


class ToolCallLog(TypedDict):
    """도구 호출 기록."""

    tool_name: str
    arguments: dict[str, Any]
    result: Any
    error: str | None


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

    Returns:
        (최종 LLM 응답, 도구 호출 로그). max_calls 도달 시에도 누적 텍스트를 반환.
    """
    if not gemini_client:
        raise RuntimeError("Gemini client not initialized")

    if max_calls is None:
        from config_pipelines import MAX_TOOL_CALLS_PER_NODE as default_max

        max_calls = default_max

    tool_logs: list[ToolCallLog] = []
    # 첫 메시지는 문자열로 전달
    contents: list[str | types.Content] = [prompt]
    call_count = 0
    # 매 스텝의 텍스트 파트를 누적 (function_call 혼재 응답에서도 보존)
    accumulated_text: list[str] = []

    config = types.GenerateContentConfig(
        tools=tools,  # type: ignore[arg-type]
        temperature=0.7,
    )

    while call_count < max_calls:
        # Gemini 호출
        async with trace_llm_call(name=f"{trace_name}_step_{call_count + 1}", input_text=prompt[:1000]) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )
            llm.record(response)

        # Tool call 감지
        if not response.candidates:
            logger.warning("[Tool-Calling] No candidates in response")
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
            # 최종 텍스트 응답
            logger.info("[Tool-Calling] Final response received (no tool calls)")
            return "\n".join(accumulated_text), tool_logs

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
    return final, tool_logs
