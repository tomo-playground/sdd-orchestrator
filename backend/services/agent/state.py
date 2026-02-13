"""ScriptState — LangGraph 상태 정의.

StoryboardRequest의 필드를 1:1 매핑하고,
중간 상태(draft)와 최종 출력(final)을 추가한다.
"""

from __future__ import annotations

from typing import TypedDict


class ScriptState(TypedDict, total=False):
    """Graph 전체에서 공유되는 상태."""

    # 입력 (StoryboardRequest 매핑)
    topic: str
    description: str
    duration: int
    style: str
    language: str
    structure: str
    actor_a_gender: str
    character_id: int | None
    character_b_id: int | None
    group_id: int | None

    # 중간 상태
    draft_scenes: list[dict] | None
    draft_character_id: int | None
    draft_character_b_id: int | None

    # 최종 출력
    final_scenes: list[dict] | None
    error: str | None
