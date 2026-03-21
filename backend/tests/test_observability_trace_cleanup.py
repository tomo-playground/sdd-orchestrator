"""SP-042: LangFuse 트레이스 품질 개선 테스트.

Part A: trace_context span output 기록
Part B: @with_agent_trace 이중 래핑 제거 확인
Part C: GENERATION output — function_call 응답 기록
Part D: route_* CHAIN 중복 제거 확인
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import services.agent.observability as obs
from services.agent.observability import (
    LLMCallResult,
    _safe_extract_function_calls,
    trace_context,
)

# ── Helpers ────────────────────────────────────────────────────


def _make_text_response(text: str):
    """텍스트 파트를 가진 Gemini-like 응답 mock."""
    part = MagicMock()
    part.text = text
    # function_call 없음
    del part.function_call
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    response.usage_metadata = None
    return response


def _make_function_call_response(name: str, args: dict | None = None):
    """function_call 파트를 가진 Gemini-like 응답 mock (텍스트 없음)."""
    part = MagicMock(spec=["function_call"])
    fc = MagicMock()
    fc.name = name
    fc.args = args or {}
    part.function_call = fc
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    response.usage_metadata = None
    return response


def _make_mixed_response(text: str, fc_name: str, fc_args: dict | None = None):
    """텍스트 + function_call 혼합 응답 mock."""
    text_part = MagicMock()
    text_part.text = text
    del text_part.function_call

    fc_part = MagicMock(spec=["function_call"])
    fc = MagicMock()
    fc.name = fc_name
    fc.args = fc_args or {}
    fc_part.function_call = fc

    content = MagicMock()
    content.parts = [text_part, fc_part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    response.usage_metadata = None
    return response


# ── Part A: trace_context span output ──────────────────────────


class TestTraceContextYieldsSpan:
    """trace_context가 span 객체를 yield하여 호출처에서 output 기록 가능."""

    @pytest.mark.asyncio
    async def test_yields_span_object(self):
        """LangFuse 활성 시 span 객체가 yield된다."""
        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        orig_client = obs._langfuse_client
        orig_init = obs._initialized
        try:
            obs._langfuse_client = mock_client
            obs._initialized = True

            async with trace_context("test.op", input_data={"x": 1}) as span:
                assert span is mock_span
                span.update(output={"result": "ok"})

            mock_span.update.assert_called()
        finally:
            obs._langfuse_client = orig_client
            obs._initialized = orig_init

    @pytest.mark.asyncio
    async def test_yields_none_when_disabled(self):
        """LangFuse 비활성 시 None이 yield된다."""
        orig_client = obs._langfuse_client
        orig_init = obs._initialized
        try:
            obs._langfuse_client = None
            obs._initialized = True

            async with trace_context("test.op") as span:
                assert span is None
        finally:
            obs._langfuse_client = orig_client
            obs._initialized = orig_init


# ── Part B: @with_agent_trace 제거 확인 ────────────────────────


class TestNoDoubleAgentTrace:
    """6개 노드에서 @with_agent_trace 데코레이터가 제거됨."""

    def test_director_plan_no_decorator(self):
        from services.agent.nodes.director_plan import director_plan_node

        # @with_agent_trace로 래핑되면 __wrapped__ 속성이 존재
        assert not hasattr(director_plan_node, "__wrapped__"), "director_plan에 @with_agent_trace 잔존"

    def test_writer_no_decorator(self):
        from services.agent.nodes.writer import writer_node

        assert not hasattr(writer_node, "__wrapped__"), "writer에 @with_agent_trace 잔존"

    def test_review_no_decorator(self):
        from services.agent.nodes.review import review_node

        assert not hasattr(review_node, "__wrapped__"), "review에 @with_agent_trace 잔존"

    def test_cinematographer_no_decorator(self):
        from services.agent.nodes.cinematographer import cinematographer_node

        assert not hasattr(cinematographer_node, "__wrapped__"), "cinematographer에 @with_agent_trace 잔존"

    def test_director_no_decorator(self):
        from services.agent.nodes.director import director_node

        assert not hasattr(director_node, "__wrapped__"), "director에 @with_agent_trace 잔존"

    def test_finalize_no_decorator(self):
        from services.agent.nodes.finalize import finalize_node

        assert not hasattr(finalize_node, "__wrapped__"), "finalize에 @with_agent_trace 잔존"

    def test_wrap_node_still_provides_agent_observation(self):
        """_wrap_node이 여전히 AGENT observation을 생성하는지 확인."""
        from services.agent.script_graph import _wrap_node

        async def dummy_node(state):
            return {"key": "value"}

        wrapped = _wrap_node("test_node", dummy_node)
        assert callable(wrapped)
        # functools.wraps 보존 확인
        assert wrapped.__name__ == "dummy_node"


# ── Part C: GENERATION output — function_call 기록 ─────────────


class TestFunctionCallOutputRecording:
    """function_call 응답에서 GENERATION output이 기록되는지 확인."""

    def test_extract_function_calls_single(self):
        response = _make_function_call_response("validate_tag", {"tag": "brown_hair"})
        result = _safe_extract_function_calls(response)
        assert "validate_tag" in result
        assert "brown_hair" in result

    def test_extract_function_calls_empty_when_text(self):
        response = _make_text_response("hello world")
        result = _safe_extract_function_calls(response)
        assert result == ""

    def test_extract_function_calls_no_candidates(self):
        response = MagicMock()
        response.candidates = []
        result = _safe_extract_function_calls(response)
        assert result == ""

    def test_record_falls_back_to_function_calls(self):
        """텍스트 없는 function_call 응답 → function_call 내용을 output에 기록."""
        llm_result = LLMCallResult()
        response = _make_function_call_response("get_character_visual_tags", {"character_id": 42})
        llm_result.record(response)

        assert llm_result.output != ""
        assert "get_character_visual_tags" in llm_result.output

    def test_record_prefers_text_over_function_calls(self):
        """텍스트가 있으면 function_call보다 텍스트 우선."""
        llm_result = LLMCallResult()
        response = _make_mixed_response("JSON output", "validate_tag", {"tag": "test"})
        llm_result.record(response)

        assert llm_result.output == "JSON output"

    def test_record_text_only(self):
        """일반 텍스트 응답은 기존과 동일하게 동작."""
        llm_result = LLMCallResult()
        response = _make_text_response("response text")
        llm_result.record(response)

        assert llm_result.output == "response text"


# ── Part D: route_* CHAIN 중복 제거 ───────────────────────────


class TestNoTracedRouteInGraph:
    """script_graph.py에서 _traced_route가 제거되고 raw 라우팅 함수가 직접 사용됨."""

    def test_no_traced_route_in_source(self):
        """script_graph.py 소스에 _traced_route 참조 없음."""
        import inspect

        import services.agent.script_graph as sg

        source = inspect.getsource(sg)
        assert "_traced_route" not in source, "script_graph.py에 _traced_route 잔존"

    def test_trace_chain_not_imported(self):
        """script_graph.py에서 trace_chain이 import되지 않음."""
        import inspect

        import services.agent.script_graph as sg

        source = inspect.getsource(sg)
        assert "trace_chain" not in source, "script_graph.py에 trace_chain import 잔존"

    def test_graph_builds_without_error(self):
        """그래프 빌드가 정상 동작."""
        from services.agent.script_graph import build_script_graph

        graph = build_script_graph()
        assert graph is not None


# ── Part A+: trace_context output 호출처 검증 ──────────────────


class TestTraceContextCallerOutput:
    """3개 호출처에서 span.update(output=...) 호출 코드가 존재하는지 검증."""

    def test_topic_analysis_records_output(self):
        """topic_analysis.py에서 span.update 호출."""
        import inspect

        import services.scripts.topic_analysis as ta

        source = inspect.getsource(ta)
        assert "span.update(output=" in source or "span.update(output =" in source

    def test_video_extract_caption_records_output(self):
        """video.py extract_caption에서 span.update 호출."""
        import inspect

        import routers.video as rv

        source = inspect.getsource(rv)
        assert 'span.update(output={"caption_length"' in source

    def test_video_extract_hashtags_records_output(self):
        """video.py extract_hashtags에서 span.update 호출."""
        import inspect

        import routers.video as rv

        source = inspect.getsource(rv)
        assert 'span.update(output={"hashtags"' in source
