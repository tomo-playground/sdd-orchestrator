"""Research 노드 단위 테스트.

InMemoryStore를 사용하여 Memory Store 연동을 검증한다.
"""

from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from services.agent.nodes.research import research_node


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def base_state():
    return {
        "topic": "테스트 주제",
        "character_id": None,
        "group_id": None,
        "mode": "full",
    }


@pytest.fixture
def config():
    return {"configurable": {"thread_id": "test-thread"}}


async def test_empty_store_returns_none(store, base_state, config):
    """빈 store에서는 research_brief가 None이다."""
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is None


async def test_character_history(store, base_state, config):
    """캐릭터 히스토리가 있으면 brief에 포함된다."""
    await store.aput(("character", "42"), "key1", {"generation_count": 5, "preferred_tone": "warm"})
    base_state["character_id"] = 42
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is not None
    assert "캐릭터" in result["research_brief"]


async def test_topic_history(store, base_state, config):
    """토픽 히스토리가 있으면 brief에 포함된다."""
    from services.agent.nodes.research import _topic_key

    topic_key = _topic_key("테스트 주제")
    await store.aput(("topic", topic_key), "key1", {"summary": "이전 생성 결과", "scene_count": 5})
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is not None
    assert "토픽" in result["research_brief"]


async def test_user_preferences(store, base_state, config):
    """사용자 선호 데이터가 있으면 brief에 포함된다."""
    await store.aput(
        ("user", "preferences"),
        "key1",
        {"total_generations": 10, "positive_ratio": 0.8},
    )
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is not None
    assert "사용자 선호" in result["research_brief"]


async def test_combined_sources(store, base_state, config):
    """여러 소스가 모두 있으면 합쳐서 brief를 구성한다."""
    from services.agent.nodes.research import _topic_key

    # Character
    await store.aput(("character", "1"), "k1", {"generation_count": 3})
    base_state["character_id"] = 1

    # Topic
    topic_key = _topic_key("테스트 주제")
    await store.aput(("topic", topic_key), "k2", {"summary": "prev"})

    # User
    await store.aput(("user", "preferences"), "k3", {"total_generations": 5})

    # Group
    await store.aput(("group", "10"), "k4", {"tone": "serious"})
    base_state["group_id"] = 10

    result = await research_node(base_state, config, store=store)
    brief = result["research_brief"]
    assert brief is not None
    assert "캐릭터" in brief
    assert "토픽" in brief
    assert "사용자 선호" in brief
    assert "그룹" in brief
