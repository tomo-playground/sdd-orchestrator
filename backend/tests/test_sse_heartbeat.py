"""SSE heartbeat 단위 테스트.

검증 항목:
1. stream_graph_events()가 graph 이벤트 사이에 heartbeat를 전송하는지
2. 정상 graph 이벤트가 heartbeat와 함께 올바르게 전달되는지
3. graph 예외 시에도 heartbeat 로직이 깨지지 않는지
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from routers._scripts_sse import SSE_HEARTBEAT_INTERVAL_SEC, stream_graph_events

_OBS = "services.agent.observability"


class _FakeAsyncIter:
    """테스트용 async iterator — 이벤트 사이에 딜레이를 시뮬레이션."""

    def __init__(self, events: list[dict], delays: list[float] | None = None):
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
    # astream()은 async iterable을 동기적으로 반환하므로 MagicMock 사용
    graph = MagicMock()
    graph.aget_state = AsyncMock(return_value=MagicMock(next=(), values={}))
    return graph


def _make_config():
    return {"callbacks": []}


def _enter_test_patches(stack: ExitStack, mock_graph: AsyncMock, *, heartbeat_interval: float | None = None) -> None:
    """테스트에 필요한 모든 patch를 ExitStack에 등록한다."""
    mock_ctx = stack.enter_context(patch("routers._scripts_sse.get_compiled_graph"))
    mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_graph)
    mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
    stack.enter_context(patch("routers._scripts_sse.preflight_safety_check", return_value=None))
    if heartbeat_interval is not None:
        stack.enter_context(patch("routers._scripts_sse.SSE_HEARTBEAT_INTERVAL_SEC", heartbeat_interval))
    for name in (
        "update_root_span",
        "flush_langfuse",
        "update_trace_on_completion",
        "update_trace_on_interrupt",
        "_patch_trace",
    ):
        stack.enter_context(patch(f"{_OBS}.{name}"))


class TestSSEHeartbeatConstant:
    def test_interval_is_15_seconds(self):
        assert SSE_HEARTBEAT_INTERVAL_SEC == 15


class TestSSEHeartbeat:
    @pytest.mark.asyncio()
    async def test_no_heartbeat_when_events_arrive_fast(self, _mock_graph):
        """이벤트가 빠르게 도착하면 heartbeat가 전송되지 않는다."""
        events = [{"research": {"result": "ok"}}, {"writer": {"draft_scenes": []}}]
        _mock_graph.astream.return_value = _FakeAsyncIter(events)

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        heartbeats = [c for c in collected if c == ":heartbeat\n\n"]
        assert len(heartbeats) == 0

    @pytest.mark.asyncio()
    async def test_heartbeat_sent_on_slow_events(self, _mock_graph):
        """이벤트 간격이 heartbeat 간격을 초과하면 heartbeat가 전송된다."""
        events = [{"research": {"result": "ok"}}]
        _mock_graph.astream.return_value = _FakeAsyncIter(events, delays=[0.3])

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph, heartbeat_interval=0.1)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        heartbeats = [c for c in collected if c == ":heartbeat\n\n"]
        data_events = [c for c in collected if c.startswith("data: ")]
        assert len(heartbeats) >= 1, "Heartbeat should be sent during slow event"
        assert len(data_events) == 1, "Graph event should still be forwarded"

    @pytest.mark.asyncio()
    async def test_heartbeat_format_is_sse_comment(self, _mock_graph):
        """Heartbeat은 SSE comment 형식 (:heartbeat\\n\\n)이다."""
        events = [{"research": {"result": "ok"}}]
        _mock_graph.astream.return_value = _FakeAsyncIter(events, delays=[0.25])

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph, heartbeat_interval=0.1)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        heartbeats = [c for c in collected if ":heartbeat" in c]
        assert len(heartbeats) >= 1, "At least one heartbeat expected"
        for hb in heartbeats:
            assert hb == ":heartbeat\n\n", "Heartbeat must be SSE comment format"
            assert hb.startswith(":"), "SSE comment must start with colon"

    @pytest.mark.asyncio()
    async def test_graph_error_propagates_with_heartbeat(self, _mock_graph):
        """Graph 스트림 에러 시에도 에러 이벤트가 정상 전달된다."""

        class _ErrorIter:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise RuntimeError("graph failed")

        _mock_graph.astream.return_value = _ErrorIter()

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        error_events = [c for c in collected if '"status": "error"' in c]
        assert len(error_events) == 1, "Error event should be forwarded"

    @pytest.mark.asyncio()
    async def test_events_interleaved_with_heartbeats(self, _mock_graph):
        """여러 이벤트 사이에 heartbeat이 올바르게 끼어들 수 있다."""
        events = [{"research": {"result": "ok"}}, {"writer": {"draft_scenes": []}}]
        _mock_graph.astream.return_value = _FakeAsyncIter(events, delays=[0.0, 0.25])

        collected = []
        with ExitStack() as stack:
            _enter_test_patches(stack, _mock_graph, heartbeat_interval=0.1)
            async for chunk in stream_graph_events({"topic": "test"}, _make_config(), "t1", "test"):
                collected.append(chunk)

        data_events = [c for c in collected if c.startswith("data: ")]
        heartbeats = [c for c in collected if c == ":heartbeat\n\n"]
        assert len(data_events) == 2, "Both graph events should be forwarded"
        assert len(heartbeats) >= 1, "At least one heartbeat during slow gap"
