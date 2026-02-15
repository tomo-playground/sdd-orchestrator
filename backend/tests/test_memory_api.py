"""Memory API 단위 테스트.

InMemoryStore를 mock하여 Memory 라우터 엔드포인트를 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.store.memory import InMemoryStore

from routers.memory import (
    delete_memory_item,
    delete_memory_namespace,
    get_memory_namespace,
    get_memory_stats,
    list_memory_items,
)


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture(autouse=True)
def mock_store(store):
    """모든 테스트에서 _get_store()가 InMemoryStore를 반환하도록 mock."""
    with patch("routers.memory._get_store", new_callable=AsyncMock, return_value=store):
        yield store


async def test_stats_empty(mock_store):
    """빈 store에서 stats는 모두 0이다."""
    result = await get_memory_stats()
    assert result.total == 0
    for count in result.by_namespace.values():
        assert count == 0


async def test_stats_with_data(mock_store):
    """데이터가 있으면 올바른 카운트를 반환한다."""
    await mock_store.aput(("character", "1"), "k1", {"count": 1})
    await mock_store.aput(("character", "2"), "k2", {"count": 2})
    await mock_store.aput(("topic", "abc"), "k3", {"summary": "test"})

    result = await get_memory_stats()
    assert result.total == 3
    assert result.by_namespace["character"] == 2
    assert result.by_namespace["topic"] == 1


async def test_list_items(mock_store):
    """타입별 항목을 올바르게 목록화한다."""
    await mock_store.aput(("character", "1"), "k1", {"name": "test"})
    result = await list_memory_items("character")
    assert result.namespace == "character"
    assert len(result.items) == 1
    assert result.items[0].key == "k1"


async def test_get_namespace(mock_store):
    """특정 네임스페이스 항목을 조회한다."""
    await mock_store.aput(("topic", "abc"), "k1", {"summary": "test1"})
    await mock_store.aput(("topic", "abc"), "k2", {"summary": "test2"})

    result = await get_memory_namespace("topic", "abc")
    assert result.namespace == "topic/abc"
    assert len(result.items) == 2


async def test_delete_item(mock_store):
    """단일 항목을 삭제한다."""
    await mock_store.aput(("character", "1"), "k1", {"name": "test"})
    result = await delete_memory_item("character", "1", "k1")
    assert result.success is True

    items = await mock_store.asearch(("character", "1"))
    assert len(items) == 0


async def test_delete_namespace(mock_store):
    """네임스페이스 전체를 삭제한다."""
    await mock_store.aput(("topic", "abc"), "k1", {"s": "1"})
    await mock_store.aput(("topic", "abc"), "k2", {"s": "2"})

    result = await delete_memory_namespace("topic", "abc")
    assert result.success is True
    assert "2개" in result.message

    items = await mock_store.asearch(("topic", "abc"))
    assert len(items) == 0
