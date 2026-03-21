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


def _mock_provider(*raw_responses):
    """LLMResponse-like 객체를 반환하는 provider mock 생성 헬퍼."""
    provider = MagicMock()
    side_effects = []
    for resp in raw_responses:
        if isinstance(resp, Exception):
            side_effects.append(resp)
        else:
            llm_resp = MagicMock()
            llm_resp.raw = resp
            llm_resp.text = ""
            side_effects.append(llm_resp)
    provider.generate_with_tools = AsyncMock(side_effect=side_effects)
    return provider


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

        mock_prov = _mock_provider(mock_response)

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="dummy_tool", description="Dummy", parameters={})]

            response, logs, _ = await call_with_tools(
                prompt="테스트 프롬프트",
                tools=tools,
                tool_executors={},
                max_calls=3,
            )

        assert response == "이것은 최종 응답입니다."
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_single_tool_call(self):
        """도구 1회 호출 후 최종 응답."""
        mock_tool_call = MagicMock()
        mock_tool_call.name = "search_history"
        mock_tool_call.args = {"topic": "테스트"}

        mock_part_with_call = MagicMock()
        mock_part_with_call.function_call = mock_tool_call
        mock_part_with_call.text = None

        mock_response_1 = MagicMock()
        mock_response_1.candidates = [
            MagicMock(content=MagicMock(parts=[mock_part_with_call])),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="검색 완료", function_call=None)],
                ),
            ),
        ]

        mock_prov = _mock_provider(mock_response_1, mock_response_2)

        def mock_executor(topic: str) -> str:
            return f"결과: {topic}"

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [
                define_tool(
                    name="search_history",
                    description="검색",
                    parameters={"topic": {"type": "string", "description": "주제"}},
                )
            ]
            tool_executors = {"search_history": mock_executor}

            response, logs, _ = await call_with_tools(
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
        mock_tool_call = MagicMock()
        mock_tool_call.name = "loop_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_response = MagicMock()
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        mock_prov = _mock_provider(mock_response, mock_response)

        def mock_executor() -> str:
            return "계속"

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="loop_tool", description="Loop", parameters={})]
            tool_executors = {"loop_tool": mock_executor}

            result_text, logs, _ = await call_with_tools(
                prompt="루프 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=2,
            )
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
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="에러 처리됨", function_call=None)],
                ),
            ),
        ]

        mock_prov = _mock_provider(mock_response_1, mock_response_2)

        def failing_executor() -> str:
            raise ValueError("의도적 에러")

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="failing_tool", description="Fail", parameters={})]
            tool_executors = {"failing_tool": failing_executor}

            response, logs, _ = await call_with_tools(
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
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="완료", function_call=None)],
                ),
            ),
        ]

        mock_prov = _mock_provider(mock_response_1, mock_response_2)

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            response, logs, _ = await call_with_tools(
                prompt="미지의 도구 테스트",
                tools=[],
                tool_executors={},
                max_calls=3,
            )

        assert response == "완료"
        assert len(logs) == 1
        assert logs[0]["tool_name"] == "unknown_tool"
        assert "not found" in logs[0]["error"]
        assert "Available tools" in logs[0]["error"]

    @pytest.mark.asyncio
    async def test_empty_text_fallback_without_tools(self):
        """tool call만 반복 → 텍스트 없음 → 도구 없이 fallback 호출."""
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

        mock_fallback_response = MagicMock()
        mock_fallback_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text='{"scenes": []}', function_call=None)],
                ),
            ),
        ]

        # max_calls=2 → 2회 tool_call + 1회 fallback
        mock_prov = _mock_provider(mock_tool_response, mock_tool_response, mock_fallback_response)

        def mock_executor() -> str:
            return "ok"

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="loop_tool", description="Loop", parameters={})]
            tool_executors = {"loop_tool": mock_executor}

            response, logs, _ = await call_with_tools(
                prompt="fallback 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=2,
            )

        assert response == '{"scenes": []}'
        assert len(logs) == 2
        # 총 3회 provider 호출 (2회 tool + 1회 fallback)
        assert mock_prov.generate_with_tools.call_count == 3

    @pytest.mark.asyncio
    async def test_fallback_not_triggered_when_text_exists(self):
        """텍스트가 있으면 fallback이 발동하지 않는다."""
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

        mock_prov = _mock_provider(mock_response)

        def mock_executor() -> str:
            return "ok"

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="some_tool", description="Some", parameters={})]
            tool_executors = {"some_tool": mock_executor}

            response, _logs, _ = await call_with_tools(
                prompt="테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=1,
            )

        assert response == '{"result": "ok"}'
        # fallback 미발동 → 1회만 호출
        assert mock_prov.generate_with_tools.call_count == 1

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

        # 1회 tool_call + fallback에서 에러
        mock_prov = _mock_provider(mock_tool_response, RuntimeError("API error"))

        def mock_executor() -> str:
            return "ok"

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="loop_tool", description="Loop", parameters={})]
            tool_executors = {"loop_tool": mock_executor}

            response, logs, _ = await call_with_tools(
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
        mock_empty_response = MagicMock()
        mock_empty_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="", function_call=None)],
                ),
            ),
        ]

        mock_fallback_response = MagicMock()
        mock_fallback_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text='{"scenes": [{"order": 1}]}', function_call=None)],
                ),
            ),
        ]

        mock_prov = _mock_provider(mock_empty_response, mock_fallback_response)

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="dummy", description="Dummy", parameters={})]

            response, logs, _ = await call_with_tools(
                prompt="빈 응답 fallback 테스트",
                tools=tools,
                tool_executors={},
                max_calls=3,
            )

        assert response == '{"scenes": [{"order": 1}]}'
        assert len(logs) == 0
        # 1회 빈 응답 + 1회 fallback = 2회 provider 호출
        assert mock_prov.generate_with_tools.call_count == 2

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

        mock_prov = _mock_provider(mock_empty_response, RuntimeError("API rate limit"))

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="dummy", description="Dummy", parameters={})]

            response, logs, _ = await call_with_tools(
                prompt="이중 실패 테스트",
                tools=tools,
                tool_executors={},
                max_calls=3,
            )

        assert response == ""
        assert len(logs) == 0
        assert mock_prov.generate_with_tools.call_count == 2

    @pytest.mark.asyncio
    async def test_hallucination_streak_breaks_loop(self):
        """연속 할루시네이션 2회 시 루프 조기 탈출 + fallback."""
        mock_tool_call = MagicMock()
        # Sentry 실제 이슈에서 관찰된 할루시네이션 도구명 (PascalCase 혼용)
        mock_tool_call.name = "Talking_tool"
        mock_tool_call.args = {}

        mock_part = MagicMock()
        mock_part.function_call = mock_tool_call
        mock_part.text = None

        mock_hallucinated_response = MagicMock()
        mock_hallucinated_response.candidates = [
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        mock_fallback_response = MagicMock()
        mock_fallback_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text='{"scenes": []}', function_call=None)],
                ),
            ),
        ]

        # 2회 할루시네이션 + 1회 fallback
        mock_prov = _mock_provider(
            mock_hallucinated_response,
            mock_hallucinated_response,
            mock_fallback_response,
        )

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="valid_tool", description="Valid", parameters={})]
            tool_executors = {"valid_tool": lambda: "ok"}

            response, logs, _ = await call_with_tools(
                prompt="할루시네이션 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=5,
            )

        # 2회 할루시네이션 후 조기 탈출, fallback으로 복구
        assert response == '{"scenes": []}'
        assert len(logs) == 2
        assert all(log["error"] and "not found" in log["error"] for log in logs)
        # 총 3회: 2회 할루시네이션 + 1회 fallback (max_calls=5이므로 5회가 아님)
        assert mock_prov.generate_with_tools.call_count == 3

    @pytest.mark.asyncio
    async def test_hallucination_streak_resets_on_valid_call(self):
        """유효한 도구 호출이 끼면 할루시네이션 streak이 리셋된다."""
        mock_hallucinated_call = MagicMock()
        mock_hallucinated_call.name = "fake_tool"
        mock_hallucinated_call.args = {}

        mock_valid_call = MagicMock()
        mock_valid_call.name = "real_tool"
        mock_valid_call.args = {}

        def _make_response(tool_call):
            part = MagicMock()
            part.function_call = tool_call
            part.text = None
            resp = MagicMock()
            resp.candidates = [MagicMock(content=MagicMock(parts=[part]))]
            return resp

        mock_text_response = MagicMock()
        mock_text_response.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text='{"ok": true}', function_call=None)],
                ),
            ),
        ]

        # 할루시네이션 → 유효 → 할루시네이션 → 텍스트 (streak 리셋으로 조기탈출 안 함)
        mock_prov = _mock_provider(
            _make_response(mock_hallucinated_call),
            _make_response(mock_valid_call),
            _make_response(mock_hallucinated_call),
            mock_text_response,
        )

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [define_tool(name="real_tool", description="Real", parameters={})]
            tool_executors = {"real_tool": lambda: "result"}

            response, logs, _ = await call_with_tools(
                prompt="리셋 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=5,
            )

        assert response == '{"ok": true}'
        # 3개 tool logs: fake_tool(error) + real_tool(ok) + fake_tool(error)
        assert len(logs) == 3
        assert logs[0]["error"] is not None
        assert logs[1]["error"] is None
        assert logs[2]["error"] is not None

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
            MagicMock(content=MagicMock(parts=[mock_part])),
        ]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="비동기 완료", function_call=None)],
                ),
            ),
        ]

        mock_prov = _mock_provider(mock_response_1, mock_response_2)

        async def async_executor(value: str) -> str:
            return f"async: {value}"

        with patch("services.agent.tools.base.get_llm_provider", return_value=mock_prov):
            tools = [
                define_tool(
                    name="async_tool",
                    description="Async",
                    parameters={"value": {"type": "string", "description": "값"}},
                )
            ]
            tool_executors = {"async_tool": async_executor}

            response, logs, _ = await call_with_tools(
                prompt="비동기 테스트",
                tools=tools,
                tool_executors=tool_executors,
                max_calls=3,
            )

        assert response == "비동기 완료"
        assert len(logs) == 1
        assert logs[0]["result"] == "async: test"
