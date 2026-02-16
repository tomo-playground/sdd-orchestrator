"""ScriptState — LangGraph 상태 정의.

StoryboardRequest의 필드를 1:1 매핑하고,
중간 상태(draft)와 최종 출력(final)을 추가한다.
"""

from __future__ import annotations

from typing import TypedDict


class SceneReasoning(TypedDict, total=False):
    """각 씬의 창작 근거."""

    narrative_function: str
    why: str
    alternatives: list[str]


class ReviewResult(TypedDict, total=False):
    """Review 노드의 검증 결과."""

    passed: bool
    errors: list[str]
    warnings: list[str]
    gemini_feedback: str | None


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

    # Graph 설정
    mode: str  # "quick" | "full"
    preset: str | None  # "quick" | "full_auto" | "creator"
    auto_approve: bool  # Full Auto에서 Human Gate 자동 승인

    # 중간 상태
    draft_scenes: list[dict] | None
    draft_character_id: int | None
    draft_character_b_id: int | None

    # Debate 결과 (Full 모드)
    debate_result: dict | None
    scene_reasoning: list[SceneReasoning] | None

    # Revision 상태
    revision_count: int
    revision_feedback: str | None

    # Human Gate 상태
    human_action: str | None  # "approve" | "revise"
    human_feedback: str | None

    # Phase 2 스텁
    research_brief: str | None
    learn_result: dict | None

    # Review 결과
    review_result: ReviewResult | None

    # Production 결과 (Full 모드)
    cinematographer_result: dict | None
    tts_designer_result: dict | None
    sound_designer_result: dict | None
    copyright_reviewer_result: dict | None

    # 최종 출력
    final_scenes: list[dict] | None
    error: str | None
