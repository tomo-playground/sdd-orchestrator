"""Script Feedback API 단위 테스트.

InMemoryStore를 사용하여 피드백 저장 + 사용자 통계 업데이트를 검증한다.
"""

from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from services.agent.feedback import update_user_preferences as _update_user_preferences


@pytest.fixture
def store():
    return InMemoryStore()


async def test_positive_feedback_creates_prefs(store):
    """첫 긍정 피드백 시 사용자 통계가 생성된다."""
    await _update_user_preferences(store, "positive")

    items = await store.asearch(("user", "preferences"))
    assert len(items) == 1
    data = items[0].value
    assert data["total_feedback"] == 1
    assert data["positive_count"] == 1
    assert data["positive_ratio"] == 1.0


async def test_negative_feedback_with_existing(store):
    """기존 통계가 있을 때 부정 피드백이 올바르게 업데이트된다."""
    # 초기 상태 설정
    await store.aput(
        ("user", "preferences"),
        "init-key",
        {
            "total_generations": 5,
            "total_feedback": 2,
            "positive_count": 2,
            "positive_ratio": 1.0,
            "feedback_themes": [],
        },
    )

    await _update_user_preferences(store, "negative")

    items = await store.asearch(("user", "preferences"))
    data = items[0].value
    assert data["total_feedback"] == 3
    assert data["positive_count"] == 2
    assert round(data["positive_ratio"], 2) == 0.67


async def test_ratio_recalculation(store):
    """여러 피드백 후 긍정 비율이 정확히 재계산된다."""
    # 3개 피드백: positive, negative, positive → 비율 = 2/3
    await _update_user_preferences(store, "positive")
    await _update_user_preferences(store, "negative")
    await _update_user_preferences(store, "positive")

    items = await store.asearch(("user", "preferences"))
    data = items[0].value
    assert data["total_feedback"] == 3
    assert data["positive_count"] == 2
    assert round(data["positive_ratio"], 2) == 0.67
