"""Learn 노드 단위 테스트.

InMemoryStore를 사용하여 학습 데이터 저장을 검증한다.
"""

from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from services.agent.nodes.learn import learn_node


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def config():
    return {"configurable": {"thread_id": "test-thread"}}


@pytest.fixture
def scenes():
    return [
        {"scene_id": 1, "script": "첫 번째 씬", "speaker": "A", "duration": 3},
        {"scene_id": 2, "script": "두 번째 씬", "speaker": "A", "duration": 3},
    ]


async def test_no_scenes_skips(store, config):
    """final_scenes가 없으면 학습을 스킵한다."""
    state = {"topic": "test", "final_scenes": None}
    result = await learn_node(state, config, store=store)
    assert result["learn_result"]["stored"] is False
    assert result["learn_result"]["reason"] == "no_scenes"


async def test_first_generation_stores(store, config, scenes):
    """첫 생성 시 토픽과 사용자 통계가 저장된다."""
    state = {"topic": "새로운 주제", "final_scenes": scenes, "structure": "Monologue"}
    result = await learn_node(state, config, store=store)
    assert result["learn_result"]["stored"] is True
    assert result["learn_result"]["scene_count"] == 2

    # user stats 확인
    user_items = await store.asearch(("user", "preferences"))
    assert len(user_items) == 1
    assert user_items[0].value["total_generations"] == 1


async def test_subsequent_generation_increments(store, config, scenes):
    """추가 생성 시 기존 통계가 증가한다."""
    # 첫 생성
    state = {"topic": "주제", "final_scenes": scenes, "structure": "Monologue"}
    await learn_node(state, config, store=store)

    # 두 번째 생성
    await learn_node(state, config, store=store)

    user_items = await store.asearch(("user", "preferences"))
    assert user_items[0].value["total_generations"] == 2


async def test_character_count_increments(store, config, scenes):
    """캐릭터 생성 횟수가 증가한다."""
    state = {"topic": "주제", "final_scenes": scenes, "character_id": 42, "structure": "Monologue"}
    await learn_node(state, config, store=store)

    char_items = await store.asearch(("character", "42"))
    assert len(char_items) == 1
    assert char_items[0].value["generation_count"] == 1

    # 두 번째
    await learn_node(state, config, store=store)
    char_items = await store.asearch(("character", "42"))
    assert char_items[0].value["generation_count"] == 2


async def test_user_stats_init(store, config, scenes):
    """사용자 통계 초기화 시 피드백 관련 필드도 포함된다."""
    state = {"topic": "주제", "final_scenes": scenes, "structure": "Monologue"}
    await learn_node(state, config, store=store)

    user_items = await store.asearch(("user", "preferences"))
    data = user_items[0].value
    assert data["total_generations"] == 1
    assert data["total_feedback"] == 0
    assert data["positive_count"] == 0
    assert data["positive_ratio"] == 0.0
