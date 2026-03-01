"""Phase 10-B-1: Gemini Function Calling 인프라 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from services.agent.tools import call_with_tools, define_tool


class TestDefineTool:
    """define_tool() 기능 테스트."""

    def test_define_tool_basic(self):
        """기본 도구 정의 테스트."""
        tool = define_tool(
            name="search_history",
            description="과거 생성 이력 검색",
            parameters={
                "topic": {"type": "string", "description": "검색 주제"},
                "limit": {"type": "integer", "description": "결과 개수"},
            },
            required=["topic"],
        )

        assert isinstance(tool, types.Tool)
        assert len(tool.function_declarations) == 1

        func_decl = tool.function_declarations[0]
        assert func_decl.name == "search_history"
        assert func_decl.description == "과거 생성 이력 검색"
        assert func_decl.parameters.type == types.Type.OBJECT
        assert "topic" in func_decl.parameters.properties
        assert "limit" in func_decl.parameters.properties

    def test_define_tool_no_required(self):
        """필수 파라미터 없는 도구 정의."""
        tool = define_tool(
            name="get_trending",
            description="트렌딩 키워드 조회",
            parameters={},
        )

        assert isinstance(tool, types.Tool)
        func_decl = tool.function_declarations[0]
        assert func_decl.parameters.required == []


class TestCallWithTools:
    """call_with_tools() 루프 테스트."""

    @pytest.mark.asyncio
    async def test_no_tool_call_direct_response(self):
        """도구 호출 없이 직접 텍스트 응답."""
        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="이것은 최종 응답입니다.", function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [
                define_tool(
                    name="dummy_tool",
                    description="Dummy",
                    parameters={},
                )
            ]
            tool_executors = {}

            response, logs = await call_with_tools(
                prompt="테스트 프롬프트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=3,
            )

        assert response == "이것은 최종 응답입니다."
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_single_tool_call(self):
        """도구 1회 호출 후 최종 응답."""
        # 첫 번째 응답: tool_call
        mock_tool_call = MagicMock()
        mock_tool_call.name = "search_history"
        mock_tool_call.args = {"topic": "테스트"}

        mock_part_with_call = MagicMock()
        mock_part_with_call.function_call = mock_tool_call
        mock_part_with_call.text = None

        mock_response_1 = MagicMock()
        mock_response_1.candidates = [
            MagicMock(
                content=MagicMock(parts=[mock_part_with_call]),
            ),
        ]

        # 두 번째 응답: 최종 텍스트
        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="검색 완료", function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_response_1, mock_response_2])

        def mock_executor(topic: str) -> str:
            return f"결과: {topic}"

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [
                define_tool(
                    name="search_history",
                    description="검색",
                    parameters={"topic": {"type": "string", "description": "주제"}},
                )
            ]
            tool_executors = {"search_history": mock_executor}

            response, logs = await call_with_tools(
                prompt="검색해줘",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=3,
            )

        assert response == "검색 완료"
        assert len(logs) == 1
        assert logs[0]["tool_name"] == "search_history"
        assert logs[0]["arguments"] == {"topic": "테스트"}
        assert logs[0]["result"] == "결과: 테스트"
        assert logs[0]["error"] is None

    @pytest.mark.asyncio
    async def test_max_calls_guard_rail(self):
        """최대 호출 횟수 가드레일 테스트."""
        # 계속 tool_call만 반환
        mock_tool_call = MagicMock()
        mock_tool_call.name = "loop_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None  # function_call 전용 파트 (텍스트 없음)

        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(
                content=MagicMock(parts=[mock_part]),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        def mock_executor() -> str:
            return "계속"

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="loop_tool", description="Loop", parameters={})]
            tool_executors = {"loop_tool": mock_executor}

            result_text, logs = await call_with_tools(
                prompt="루프 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=2,
            )
            # max_calls 도달 시에도 정상 반환 (누적 텍스트 + 로그)
            assert isinstance(result_text, str)
            assert len(logs) == 2  # 2번 도구 호출

    @pytest.mark.asyncio
    async def test_tool_executor_error(self):
        """도구 실행 에러 핸들링."""
        mock_tool_call = MagicMock()
        mock_tool_call.name = "failing_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_response_1 = MagicMock()
        mock_response_1.candidates = [
            MagicMock(
                content=MagicMock(parts=[mock_part]),
            ),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="에러 처리됨", function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_response_1, mock_response_2])

        def failing_executor() -> str:
            raise ValueError("의도적 에러")

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="failing_tool", description="Fail", parameters={})]
            tool_executors = {"failing_tool": failing_executor}

            response, logs = await call_with_tools(
                prompt="에러 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=3,
            )

        assert response == "에러 처리됨"
        assert len(logs) == 1
        assert logs[0]["tool_name"] == "failing_tool"
        assert logs[0]["result"] is None
        assert "ValueError: 의도적 에러" in logs[0]["error"]

    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        """존재하지 않는 도구 호출 시 에러 로깅."""
        mock_tool_call = MagicMock()
        mock_tool_call.name = "unknown_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_response_1 = MagicMock()
        mock_response_1.candidates = [
            MagicMock(
                content=MagicMock(parts=[mock_part]),
            ),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="완료", function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_response_1, mock_response_2])

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = []
            tool_executors = {}

            response, logs = await call_with_tools(
                prompt="미지의 도구 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=3,
            )

        assert response == "완료"
        assert len(logs) == 1
        assert logs[0]["tool_name"] == "unknown_tool"
        assert "not found in executors" in logs[0]["error"]

    @pytest.mark.asyncio
    async def test_empty_text_fallback_without_tools(self):
        """tool call만 반복 → 텍스트 없음 → 도구 없이 fallback 호출."""
        # 모든 응답이 tool_call만 포함 (텍스트 없음)
        mock_tool_call = MagicMock()
        mock_tool_call.name = "loop_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_tool_response = MagicMock()
        mock_tool_response.candidates = [
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        # fallback 응답 (도구 없이 호출 → 텍스트 반환)
        mock_fallback_response = MagicMock()
        mock_fallback_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text='{"scenes": []}', function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        # max_calls=2 → 2회 tool_call + 1회 fallback
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[mock_tool_response, mock_tool_response, mock_fallback_response],
        )

        def mock_executor() -> str:
            return "ok"

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="loop_tool", description="Loop", parameters={})]
            tool_executors = {"loop_tool": mock_executor}

            response, logs = await call_with_tools(
                prompt="fallback 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=2,
            )

        assert response == '{"scenes": []}'
        assert len(logs) == 2
        # 총 3회 Gemini 호출 (2회 tool + 1회 fallback)
        assert mock_client.aio.models.generate_content.call_count == 3

    @pytest.mark.asyncio
    async def test_fallback_not_triggered_when_text_exists(self):
        """텍스트가 있으면 fallback이 발동하지 않는다."""
        # 첫 응답: tool_call + 텍스트 혼재
        mock_tool_call = MagicMock()
        mock_tool_call.name = "some_tool"
        mock_tool_call.args = {}

        mock_part_tool = MagicMock()
        mock_part_tool.function_call = mock_tool_call
        mock_part_tool.text = None

        mock_part_text = MagicMock()
        mock_part_text.function_call = None
        mock_part_text.text = '{"result": "ok"}'

        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[mock_part_text, mock_part_tool])),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        def mock_executor() -> str:
            return "ok"

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="some_tool", description="Some", parameters={})]
            tool_executors = {"some_tool": mock_executor}

            response, _logs = await call_with_tools(
                prompt="테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=1,
            )

        assert response == '{"result": "ok"}'
        # fallback 미발동 → 1회만 호출
        assert mock_client.aio.models.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_failure_returns_empty(self):
        """fallback 호출 실패 시에도 빈 문자열로 정상 반환."""
        mock_tool_call = MagicMock()
        mock_tool_call.name = "loop_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_tool_response = MagicMock()
        mock_tool_response.candidates = [
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        mock_client = MagicMock()
        # 1회 tool_call + fallback에서 에러
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[mock_tool_response, RuntimeError("API error")],
        )

        def mock_executor() -> str:
            return "ok"

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="loop_tool", description="Loop", parameters={})]
            tool_executors = {"loop_tool": mock_executor}

            response, logs = await call_with_tools(
                prompt="실패 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=1,
            )

        assert response == ""
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_empty_final_response_triggers_fallback(self):
        """도구 호출 없이 빈 텍스트 응답 → fallback 호출로 복구."""
        # Gemini가 빈 텍스트(또는 공백만) 반환하는 경우
        mock_empty_response = MagicMock()
        mock_empty_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="", function_call=None)],
                ),
            ),
        ]

        # fallback 응답 (도구 없이 호출 → 텍스트 반환)
        mock_fallback_response = MagicMock()
        mock_fallback_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text='{"scenes": [{"order": 1}]}', function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[mock_empty_response, mock_fallback_response],
        )

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="dummy", description="Dummy", parameters={})]

            response, logs = await call_with_tools(
                prompt="빈 응답 fallback 테스트",
                tools=tools,
                tool_executors={},
                max_calls=3,
            )

        assert response == '{"scenes": [{"order": 1}]}'
        assert len(logs) == 0
        # 1회 빈 응답 + 1회 fallback = 2회 호출
        assert mock_client.aio.models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_final_response_fallback_also_fails(self):
        """빈 텍스트 응답 + fallback도 실패 → 빈 문자열 반환."""
        mock_empty_response = MagicMock()
        mock_empty_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text=None, function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[mock_empty_response, RuntimeError("API rate limit")],
        )

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [define_tool(name="dummy", description="Dummy", parameters={})]

            response, logs = await call_with_tools(
                prompt="이중 실패 테스트",
                tools=tools,
                tool_executors={},
                max_calls=3,
            )

        assert response == ""
        assert len(logs) == 0
        assert mock_client.aio.models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_async_tool_executor(self):
        """비동기 도구 실행 테스트."""
        mock_tool_call = MagicMock()
        mock_tool_call.name = "async_tool"
        mock_tool_call.args = {"value": "test"}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_response_1 = MagicMock()
        mock_response_1.candidates = [
            MagicMock(
                content=MagicMock(parts=[mock_part]),
            ),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="비동기 완료", function_call=None)],
                ),
            ),
        ]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_response_1, mock_response_2])

        async def async_executor(value: str) -> str:
            return f"async: {value}"

        with (
            patch("services.agent.tools.base.gemini_client", mock_client),
            patch("services.agent.tools.base.trace_llm_call") as mock_trace,
        ):
            mock_trace.return_value.__aenter__ = AsyncMock(return_value=MagicMock(record=MagicMock()))
            mock_trace.return_value.__aexit__ = AsyncMock(return_value=None)

            tools = [
                define_tool(
                    name="async_tool",
                    description="Async",
                    parameters={"value": {"type": "string", "description": "값"}},
                )
            ]
            tool_executors = {"async_tool": async_executor}

            response, logs = await call_with_tools(
                prompt="비동기 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=3,
            )

        assert response == "비동기 완료"
        assert len(logs) == 1
        assert logs[0]["result"] == "async: test"
