"""피드백 관련 store 헬퍼."""

from __future__ import annotations

import uuid

from langgraph.store.base import BaseStore


async def update_user_preferences(store: BaseStore, rating: str) -> None:
    """user preferences의 피드백 카운트를 갱신한다."""
    user_ns = ("user", "preferences")
    existing = await store.asearch(user_ns)
    is_positive = 1 if rating == "positive" else 0

    if existing:
        prefs = existing[0].value
        total = prefs.get("total_feedback", 0) + 1
        positive = prefs.get("positive_count", 0) + is_positive
        prefs["total_feedback"] = total
        prefs["positive_count"] = positive
        prefs["positive_ratio"] = round(positive / total, 2) if total > 0 else 0
        await store.aput(user_ns, existing[0].key, prefs)
    else:
        await store.aput(
            user_ns,
            str(uuid.uuid4()),
            {
                "total_generations": 0,
                "total_feedback": 1,
                "positive_count": is_positive,
                "positive_ratio": float(is_positive),
                "feedback_themes": [],
            },
        )
