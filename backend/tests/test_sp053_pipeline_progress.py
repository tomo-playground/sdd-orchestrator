"""SP-053: 파이프라인 진행 표시 테스트.

검증 항목:
1. _build_starting_payload() — 시작 이벤트 SSE 형식
2. stream_mode=["updates", "custom"] 이벤트 파싱
3. with_starting_event() 데코레이터 동작
4. get_trace_url() 활성/비활성
5. completion/error payload에 trace_url 포함
"""

from __future__ import annotations

import asyncio
import json
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from routers._scripts_sse import NODE_META, _build_starting_payload, stream_graph_events

_OBS = "services.agent.observability"


class _FakeAsyncIter:
    """stream_mode=["updates", "custom"] tuple 형식 이벤트 시뮬레이터."""

    def __init__(self, events: list, delays: list[float] | None = None):
        self._events = events
        self._delays = delays or [0.0] * len(events)
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._events):
            raise StopAsyncIteration
        delay = self._delays[self._idx] if self._idx < len(self._delays) else 0
        if delay > 0:
            await asyncio.sleep(delay)
        event = self._events[self._idx]
        self._idx += 1
        return event


@pytest.fixture()
def _mock_graph():
    graph = MagicMock()
    graph.aget_state = AsyncMock(return_value=MagicMock(next=(), values={}))
    return graph


def _make_config():
    return {"callbacks": []}


def _enter_test_patches(stack: ExitStack, mock_graph: AsyncMock, *, trace_url: str | None = None) -> None:
    mock_ctx = stack.enter_context(patch("routers._scripts_sse.get_compiled_graph"))
    mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_graph)
    mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
    stack.enter_context(patch("routers._scripts_sse.preflight_safety_check", return_value=None))
    for name in (
        "update_root_span",
        "flush_langfuse",
        "update_trace_on_completion",
        "update_trace_on_interrupt",
        "_patch_trace",
    ):
        stack.enter_context(patch(f"{_OBS}.{name}"))
    stack.enter_context(patch(f"{_OBS}.get_trace_url", return_value=trace_url))


class TestBuildStartingPayload:
    def test_known_node_returns_correct_format(self):
        result = _build_starting_payload("writer", "t1")
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        data = json.loads(result[6:])
        assert data["node"] == "writer"
        assert data["status"] == "starting"
        assert data["label"] == "대본 생성"
        assert data["percent"] == NODE_META["writer"]["percent"] - 5
        assert data["thread_id"] == "t1"

    def test_unknown_node_uses_fallback(self):
        result = _build_starting_payload("unknown_node", "t2")
        data = json.loads(result[6:])
        assert data["node"] == "unknown_node"
        assert data["label"] == "unknown_node"
        assert data["percent"] == 45  # max(1, 50 - 5)
        assert data["status"] == "starting"

    def test_starting_percent_minimum_is_one(self):
        result = _build_starting_payload("director_plan", "t3")
        data = json.loads(result[6:])
        # director_plan percent=3, starting=max(1, 3-5)=1
        assert data["percent"] == 1


class TestStreamCustomEvents:
    @pytest.mark.asyncio()
    async def test_starting_event_yielded_before_updates(self, _mock_graph):
        """custom 이벤트(starting)가 updates 이벤트 전에 yield된다."""
        events = [
            ("custom", {"type": "node_starting", "node": "writer"}),
            ("updates", {"writer": {"draft_scenes": []}}),
        ]
        _mock_graph.astream.return_value = _FakeAsyncIter(events)

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        data_events = [c for c in collected if c.startswith("data: ")]
        assert len(data_events) == 2

        first = json.loads(data_events[0][6:])
        assert first["status"] == "starting"
        assert first["node"] == "writer"

        second = json.loads(data_events[1][6:])
        assert second["status"] == "running"
        assert second["node"] == "writer"

    @pytest.mark.asyncio()
    async def test_non_starting_custom_events_ignored(self, _mock_graph):
        """type이 node_starting이 아닌 custom 이벤트는 무시된다."""
        events = [
            ("custom", {"type": "other_event", "data": "test"}),
            ("updates", {"research": {"result": "ok"}}),
        ]
        _mock_graph.astream.return_value = _FakeAsyncIter(events)

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        data_events = [c for c in collected if c.startswith("data: ")]
        assert len(data_events) == 1
        first = json.loads(data_events[0][6:])
        assert first["node"] == "research"


class TestWithStartingEvent:
    @pytest.mark.asyncio()
    async def test_decorator_calls_stream_writer(self):
        """with_starting_event 데코레이터가 stream_writer를 호출한다."""
        from services.agent.observability import with_starting_event

        mock_writer = MagicMock()

        async def dummy_node(state):
            return {"result": "ok"}

        decorated = with_starting_event("test_node")(dummy_node)

        with patch("langgraph.config.get_stream_writer", return_value=mock_writer):
            result = await decorated({})

        mock_writer.assert_called_once_with({"type": "node_starting", "node": "test_node"})
        assert result == {"result": "ok"}

    @pytest.mark.asyncio()
    async def test_decorator_graceful_when_no_writer(self):
        """stream_writer가 없을 때도 노드 함수는 정상 실행된다."""
        from services.agent.observability import with_starting_event

        async def dummy_node(state):
            return {"result": "ok"}

        decorated = with_starting_event("test_node")(dummy_node)

        with patch("langgraph.config.get_stream_writer", side_effect=RuntimeError("no writer")):
            result = await decorated({})

        assert result == {"result": "ok"}


class TestGetTraceUrl:
    def test_returns_url_when_enabled(self):
        from services.agent.observability import _current_trace_id, get_trace_url

        token = _current_trace_id.set("abc123")
        try:
            with patch(f"{_OBS}.LANGFUSE_ENABLED", True), patch(f"{_OBS}.LANGFUSE_BASE_URL", "http://lf:3001"):
                url = get_trace_url()
            assert url == "http://lf:3001/trace/abc123"
        finally:
            _current_trace_id.reset(token)

    def test_returns_none_when_disabled(self):
        from services.agent.observability import _current_trace_id, get_trace_url

        token = _current_trace_id.set("abc123")
        try:
            with patch(f"{_OBS}.LANGFUSE_ENABLED", False):
                url = get_trace_url()
            assert url is None
        finally:
            _current_trace_id.reset(token)

    def test_returns_none_when_no_trace_id(self):
        from services.agent.observability import _current_trace_id, get_trace_url

        token = _current_trace_id.set(None)
        try:
            url = get_trace_url()
            assert url is None
        finally:
            _current_trace_id.reset(token)


class TestTraceUrlInPayloads:
    @pytest.mark.asyncio()
    async def test_completion_payload_includes_trace_url(self, _mock_graph):
        """finalize 완료 시 trace_url이 포함된다."""
        events = [
            ("updates", {"finalize": {"final_scenes": [{"script": "test"}], "structure": "monologue"}}),
            ("updates", {"explain": {"explanation_result": {}}}),
            ("updates", {"learn": {}}),
        ]
        _mock_graph.astream.return_value = _FakeAsyncIter(events)

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph, trace_url="http://lf:3001/trace/abc")
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        finalize_events = [c for c in collected if c.startswith("data: ") and '"finalize"' in c]
        assert len(finalize_events) == 1
        data = json.loads(finalize_events[0][6:])
        assert data["trace_url"] == "http://lf:3001/trace/abc"

    @pytest.mark.asyncio()
    async def test_error_payload_includes_trace_url(self, _mock_graph):
        """에러 시 trace_url이 포함된다."""

        class _ErrorIter:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise RuntimeError("graph failed")

        _mock_graph.astream.return_value = _ErrorIter()

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph, trace_url="http://lf:3001/trace/err")
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        error_events = [c for c in collected if c.startswith("data: ") and '"error"' in c]
        assert len(error_events) == 1
        data = json.loads(error_events[0][6:])
        assert data["trace_url"] == "http://lf:3001/trace/err"

    @pytest.mark.asyncio()
    async def test_no_trace_url_when_none(self, _mock_graph):
        """trace_url이 None이면 payload에 포함되지 않는다."""
        events = [
            ("updates", {"finalize": {"final_scenes": [{"script": "test"}]}}),
            ("updates", {"learn": {}}),
        ]
        _mock_graph.astream.return_value = _FakeAsyncIter(events)

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph, trace_url=None)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        finalize_events = [c for c in collected if c.startswith("data: ") and '"finalize"' in c]
        data = json.loads(finalize_events[0][6:])
        assert "trace_url" not in data


class TestNodeMetaCompleteness:
    def test_location_planner_in_meta(self):
        assert "location_planner" in NODE_META
        assert NODE_META["location_planner"]["label"] == "로케이션 설계"

    def test_director_checkpoint_in_meta(self):
        assert "director_checkpoint" in NODE_META
        assert NODE_META["director_checkpoint"]["label"] == "연출 판단"
