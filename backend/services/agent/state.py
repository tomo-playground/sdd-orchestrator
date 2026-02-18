"""ScriptState — LangGraph 상태 정의.

StoryboardRequest의 필드를 1:1 매핑하고,
중간 상태(draft)와 최종 출력(final)을 추가한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    pass


class SceneReasoning(TypedDict, total=False):
    """각 씬의 창작 근거."""

    narrative_function: str
    why: str
    alternatives: list[str]


class NarrativeScore(TypedDict, total=False):
    """서사 품질 평가 결과 (Full 모드 전용)."""

    hook: float  # 0.0-1.0
    emotional_arc: float
    twist_payoff: float
    speaker_tone: float
    script_image_sync: float
    overall: float  # 가중 평균
    feedback: str  # 개선 제안 (한국어)


class ReviewResult(TypedDict, total=False):
    """Review 노드의 검증 결과."""

    passed: bool
    errors: list[str]
    warnings: list[str]
    gemini_feedback: str | None
    narrative_score: NarrativeScore | None


class DirectorReActStep(TypedDict):
    """Director의 각 ReAct 스텝 (Phase 10-A)."""

    step: int  # 1-3
    observe: str  # 관찰 내용
    think: str  # 사고 과정
    act: str  # 행동 결정


class WriterPlan(TypedDict):
    """Writer의 계획 수립 결과 (Phase 10-A)."""

    hook_strategy: str  # Hook 전략
    emotional_arc: list[str]  # 감정 곡선 (씬별)
    scene_distribution: dict[str, int]  # 구조별 씬 배분


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
    references: list[str] | None  # 소재 URL/텍스트 목록

    # Graph 설정
    mode: str  # "quick" | "full"
    preset: str | None  # "quick" | "full_auto" | "creator"
    auto_approve: bool  # Full Auto에서 Human Gate 자동 승인

    # 중간 상태
    draft_scenes: list[dict] | None
    draft_character_id: int | None
    draft_character_b_id: int | None

    # Writer Planning (Phase 10-A)
    writer_plan: WriterPlan | None

    # Tool-Calling (Phase 10-B)
    research_tool_logs: list[dict] | None
    cinematographer_tool_logs: list[dict] | None

    # Critic 결과 (Full 모드)
    critic_result: dict | None
    scene_reasoning: list[SceneReasoning] | None

    # Concept Gate 상태
    concept_action: str | None  # "select" | "regenerate"
    concept_regen_count: int  # 컨셉 재생성 횟수

    # Revision 상태
    revision_count: int
    revision_feedback: str | None

    # Human Gate 상태
    human_action: str | None  # "approve" | "revise"
    human_feedback: str | None

    # Phase 2 Research & Learn
    research_brief: str | None
    research_tool_logs: list[dict] | None  # Phase 10-B-2: Tool-Calling 로그
    learn_result: dict | None

    # Review 결과
    review_result: ReviewResult | None
    review_reflection: str | None  # Phase 10-A: Self-Reflection (실패 원인 분석 + 수정 전략)

    # Production 결과 (Full 모드)
    cinematographer_result: dict | None
    cinematographer_tool_logs: list[dict] | None  # Phase 10-B-3: Tool-Calling 로그
    tts_designer_result: dict | None
    sound_designer_result: dict | None
    copyright_reviewer_result: dict | None

    # Director 결과 (Full 모드)
    director_decision: str | None
    director_feedback: str | None
    director_revision_count: int
    director_reasoning_steps: list[DirectorReActStep] | None  # Phase 10-A: ReAct Loop 사고 과정

    # Explain 결과 (Full 모드)
    explanation_result: dict | None

    # Agent Communication (Phase 10-C)
    agent_messages: list[dict] | None  # AgentMessage 타입 (messages.py)
    agent_summary: str | None  # 압축된 메시지 요약
    debate_log: list[dict] | None  # Phase 10-C-3: Critic 토론 기록 (라운드별 비평/개선)

    # 최종 출력
    final_scenes: list[dict] | None
    error: str | None
