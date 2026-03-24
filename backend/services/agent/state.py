"""ScriptState — LangGraph 상태 정의.

StoryboardRequest의 필드를 1:1 매핑하고,
중간 상태(draft)와 최종 출력(final)을 추가한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    pass


class DirectorPlan(TypedDict, total=False):
    """Director의 초기 목표 수립 결과."""

    creative_goal: str  # 영상 핵심 목표 (1문장)
    target_emotion: str  # 타겟 감정
    quality_criteria: list[str]  # 품질 기준 3-5개
    risk_areas: list[str]  # 예상 위험 요소
    style_direction: str  # 스타일 방향
    visual_direction: str  # 비주얼 방향 (톤, 서사 구조, 클라이막스 위치)


class CineTeamResult(TypedDict, total=False):
    """Cinematographer 팀 서브 에이전트 중간 결과."""

    framing: dict  # Framing Agent 출력 (camera, gaze, ken_burns per scene)
    action: dict  # Action Agent 출력 (action, pose, emotion, props per scene)
    atmosphere: dict  # Atmosphere Agent 출력 (environment, cinematic per scene)


class SceneReasoning(TypedDict, total=False):
    """각 씬의 창작 근거."""

    narrative_function: str
    why: str
    alternatives: list[str]


class ResearchScore(TypedDict, total=False):
    """Research 노드 품질 점수 (규칙 기반)."""

    tool_success_rate: float  # 성공 도구 호출 / 전체 호출
    information_density: float  # brief 길이 기반
    source_diversity: float  # 고유 도구 종류 수 / 유효 도구 수
    topic_coverage: float  # brief에 topic 관련 신호 포함 여부
    overall: float  # 가중 평균 (0.0-1.0)
    feedback: str  # 개선 제안


class NarrativeScore(TypedDict, total=False):
    """서사 품질 평가 결과 (Full 모드 전용)."""

    hook: float  # 0.0-1.0
    emotional_arc: float
    twist_payoff: float
    speaker_tone: float
    script_image_sync: float
    spoken_naturalness: float  # TTS 낭독 자연스러움 (AI톤 감지)
    retention_flow: float  # 씬→씬 호기심 연결
    pacing_rhythm: float  # 템포/리듬 변화
    situational_specificity: float  # 상황 구체성
    overall: float  # 가중 평균
    feedback: str  # 개선 제안 (한국어)
    scene_issues: list[dict]  # per-scene 서사 이슈 (SP-064)


class ReviewResult(TypedDict, total=False):
    """Review 노드의 검증 결과."""

    passed: bool
    errors: list[str]  # AI용 구체적 피드백 (Revise 노드가 사용)
    warnings: list[str]  # AI용 경고 메시지
    gemini_feedback: str | None
    narrative_score: NarrativeScore | None
    user_summary: str  # 사용자용 요약 메시지 (Frontend 표시용)


class DirectorReActStep(TypedDict):
    """Director의 각 ReAct 스텝 (Phase 10-A)."""

    step: int  # 1-3
    observe: str  # 관찰 내용
    think: str  # 사고 과정
    act: str  # 행동 결정
    feedback: str  # revise 시 피드백 내용 (approve 시 빈 문자열)


class _WriterPlanRequired(TypedDict):
    """Writer Plan 필수 필드."""

    hook_strategy: str  # Hook 전략
    emotional_arc: list[str]  # 감정 곡선 (씬별)
    scene_distribution: dict[str, int]  # 구조별 씬 배분


class WriterPlan(_WriterPlanRequired, total=False):
    """Writer의 계획 수립 결과 (Phase 10-A)."""

    locations: list[dict]  # 장소 맵: [{name, scenes, tags}] — LocationPlan | dict 양방향 호환


def get_loc_field(loc: object, field: str, default: object = None) -> object:
    """Read a field from a location entry (dict or Pydantic model).

    LangGraph checkpoint deserialization returns plain dict even if the
    original value was a Pydantic model. This helper safely accesses
    fields from both dict and attribute-based objects.
    """
    if isinstance(loc, dict):
        return loc.get(field, default)
    return getattr(loc, field, default)


class ScriptState(TypedDict, total=False):
    """Graph 전체에서 공유되는 상태."""

    # 입력 (StoryboardRequest 매핑)
    topic: str
    description: str
    duration: int
    style: str
    language: str
    structure: str
    tone: str
    actor_a_gender: str
    character_id: int | None
    character_b_id: int | None
    group_id: int | None
    references: list[str] | None  # 소재 URL/텍스트 목록

    # Intake 결과 (Guided 모드 — 의도 파악)
    intake_summary: str  # 결정 요약 (예: "학교 괴담, 대화형, 서스펜스, 미도리↔하루")

    # Graph 설정
    preset: str | None  # deprecated — 향후 제거 예정
    skip_stages: list[str]  # ["research", "concept", "production"]
    interaction_mode: str  # "guided" | "fast_track"
    chat_context: list[dict] | None  # 사전 대화 이력 [{role, text}]
    plan_action: str | None  # "proceed" | "revise" (Director Plan Gate 결과)
    plan_revision_count: int  # Director Plan 재수정 횟수

    # 중간 상태
    draft_scenes: list[dict] | None
    draft_character_id: int | None
    draft_character_b_id: int | None

    # Writer Planning (Phase 10-A)
    writer_plan: WriterPlan | None

    # Critic 결과 (Full 모드)
    critic_result: dict | None
    scene_reasoning: list[SceneReasoning] | None

    # Concept Gate 상태
    concept_action: str | None  # "select" | "regenerate"
    concept_regen_count: int  # 컨셉 재생성 횟수

    # Revision 상태
    revision_count: int
    revision_feedback: str | None
    revision_history: list[dict] | None  # 누적 히스토리 (attempt, errors, reflection, score, tier)
    best_draft_scenes: list[dict] | None  # 최고 narrative_score 시점의 scenes 스냅샷
    best_narrative_score: float  # 최고 narrative_score.overall (rollback 기준)

    # Human Gate 상태
    human_action: str | None  # "approve" | "revise" | "required" (halt sentinel)
    human_feedback: str | None
    human_gate_reason: str | None  # halt sentinel 사유 (예: "checkpoint_fallback")

    # Phase 2 Research & Learn
    research_brief: str | dict | None
    research_tool_logs: list[dict] | None  # Phase 10-B-2: Tool-Calling 로그
    research_score: ResearchScore | None  # 규칙 기반 품질 점수
    research_retry_count: int  # Research 재실행 횟수
    learn_result: dict | None

    # Review 결과
    review_result: ReviewResult | None
    review_reflection: str | None  # Phase 10-A: Self-Reflection (실패 원인 분석 + 수정 전략)

    # Production 결과 (Full 모드)
    cinematographer_result: dict | None
    cinematographer_tool_logs: list[dict] | None  # Phase 10-B-3: Tool-Calling 로그
    visual_qc_result: dict | None  # Cinematographer QC → Director 전달용
    tts_qc_result: dict | None  # TTS Designer QC → Director 전달용
    sound_qc_result: dict | None  # Sound Designer QC → Director 전달용
    copyright_qc_result: dict | None  # Copyright Reviewer QC → Director 전달용
    cinematographer_competition_scores: dict | None  # {"tension": 0.82, "intimacy": 0.75, ...}
    cinematographer_winner: str | None  # 경쟁 승자 role (예: "tension")
    tts_designer_result: dict | None
    sound_designer_result: dict | None
    copyright_reviewer_result: dict | None

    # Phase 20-A: Director Inventory Awareness
    casting_recommendation: dict | None  # CastingRecommendation (Pydantic → dict)
    valid_character_ids: list[int] | None  # 인벤토리 캐릭터 ID 목록 (검증용)

    # Director Plan (Full 모드 — 초기 목표 수립)
    director_plan: DirectorPlan | None
    director_checkpoint_decision: str | None  # "proceed" | "revise"
    director_checkpoint_feedback: str | None
    director_checkpoint_score: float | None
    director_checkpoint_revision_count: int

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
    sound_recommendation: dict | None
    copyright_result: dict | None
    error: str | None


def build_director_context(state: ScriptState) -> str | None:
    """Director Plan 컨텍스트 문자열을 생성한다. director_plan 없으면 None."""
    director_plan = state.get("director_plan")
    if not director_plan:
        return None
    return (
        f"크리에이티브 목표: {director_plan.get('creative_goal', '')}\n"
        f"타겟 감정: {director_plan.get('target_emotion', '')}\n"
        f"품질 기준: {', '.join(director_plan.get('quality_criteria', []))}"
    )


def extract_selected_concept(state: ScriptState) -> dict | None:
    """critic_result에서 selected_concept를 추출한다. 없으면 None."""
    critic_result = state.get("critic_result")
    if not critic_result:
        return None
    selected = critic_result.get("selected_concept")
    return selected if selected else None
