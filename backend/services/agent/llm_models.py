"""LLM 출력 검증용 Pydantic 모델.

Gemini LLM 응답을 JSON 파싱 후, ScriptState(TypedDict)에 기록하기 전에
Pydantic v2 모델로 런타임 검증한다.

사용 패턴:
  validate_fn=lambda data: validate_with_model(DirectorPlanOutput, data).model_dump()
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from config import MULTI_CHAR_STRUCTURES


class QCResult(BaseModel):
    """validate_fn 호환 QC 결과 포맷."""

    ok: bool
    issues: list[str] = []
    checks: dict[str, str] = {}


# -- Phase 20-A: Casting Recommendation --


class CastingRecommendation(BaseModel):
    """Director의 캐스팅 추천."""

    character_a_id: int | None = None  # Speaker A 캐릭터 ID
    character_a_name: str = ""  # Speaker A 캐릭터 이름
    character_b_id: int | None = None  # Speaker B 캐릭터 ID
    character_b_name: str = ""  # Speaker B 캐릭터 이름
    structure: str | None = None
    reasoning: str = ""

    @field_validator("character_a_name", "character_b_name", "reasoning", mode="before")
    @classmethod
    def _coerce_none_to_empty(cls, v: object) -> str:  # noqa: ANN401
        """Gemini가 null을 명시 반환할 때 빈 문자열로 변환."""
        return str(v) if v is not None else ""

    @model_validator(mode="after")
    def _validate_casting(self) -> CastingRecommendation:
        """2인 구조 시 character_b_id 없으면 monologue로 강등, 중복 ID 방지."""
        if self.structure in MULTI_CHAR_STRUCTURES and self.character_a_id and not self.character_b_id:
            self.structure = "monologue"
        if self.character_a_id and self.character_a_id == self.character_b_id:
            self.character_b_id = None
            self.character_b_name = ""
            self.structure = "monologue"
        return self


# -- Director Plan --


class ExecutionPlan(BaseModel):
    """Director가 토픽 복잡도를 분석하여 결정하는 실행 계획."""

    run_research: bool = True
    # concept(Critic 토론)은 항상 실행 — AI 자율 스킵 불가 (_derive_skip_stages 참고)
    # 이 필드는 LLM 출력 호환성 유지를 위해 보존하지만 skip_stages에 영향 없음
    run_concept: bool = True
    run_explain: bool = True
    reasoning: str = ""


class DirectorPlanOutput(BaseModel):
    """Director Plan 노드의 LLM 응답."""

    creative_goal: str = Field(min_length=1)
    target_emotion: str = Field(min_length=1)
    quality_criteria: list[str] = Field(min_length=1)
    risk_areas: list[str] = []
    style_direction: str = ""
    visual_direction: str = ""
    casting: CastingRecommendation | None = None
    execution_plan: ExecutionPlan = Field(default_factory=ExecutionPlan)


# -- Director ReAct --

_VALID_ACT_DECISIONS = Literal[
    "approve",
    "revise_cinematographer",
    "revise_tts",
    "revise_sound",
    "revise_script",
]


class DirectorReActOutput(BaseModel):
    """Director ReAct 노드의 LLM 응답 (Observe→Think→Act)."""

    observe: str = Field(min_length=1)
    think: str = Field(min_length=1)
    act: _VALID_ACT_DECISIONS
    feedback: str = ""

    @field_validator("feedback", mode="before")
    @classmethod
    def _coerce_feedback(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)

    @model_validator(mode="after")
    def _feedback_required_for_revise(self) -> DirectorReActOutput:
        if self.act != "approve" and not self.feedback:
            msg = "feedback required for revise_* actions"
            raise ValueError(msg)
        return self


# -- Director Checkpoint --


class DirectorCheckpointOutput(BaseModel):
    """Director Checkpoint 노드의 LLM 응답."""

    decision: Literal["proceed", "revise"]
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)
    feedback: str = ""

    @field_validator("feedback", mode="before")
    @classmethod
    def _coerce_feedback(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)

    @model_validator(mode="after")
    def _feedback_required_for_revise(self) -> DirectorCheckpointOutput:
        if self.decision == "revise" and not self.feedback:
            msg = "feedback required when decision is 'revise'"
            raise ValueError(msg)
        return self


# -- Narrative Score --


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class NarrativeScoreOutput(BaseModel):
    """Review 노드의 서사 품질 평가 (NarrativeScore)."""

    hook: float = 0.0
    emotional_arc: float = 0.0
    twist_payoff: float = 0.0
    speaker_tone: float = 0.0
    script_image_sync: float = 0.0
    spoken_naturalness: float = 0.0  # TTS 낭독 자연스러움
    retention_flow: float = 0.0  # 씬→씬 호기심 연결
    pacing_rhythm: float = 0.0  # 템포/리듬 변화
    feedback: str = ""
    scene_issues: list[dict] = []  # per-scene 서사 이슈 (SP-064)

    @model_validator(mode="before")
    @classmethod
    def _clamp_scores(cls, data: dict) -> dict:  # type: ignore[override]
        if not isinstance(data, dict):
            return data
        out = dict(data)
        score_keys = (
            "hook",
            "emotional_arc",
            "twist_payoff",
            "speaker_tone",
            "script_image_sync",
            "spoken_naturalness",
            "retention_flow",
            "pacing_rhythm",
        )
        for k in score_keys:
            v = out.get(k)
            if isinstance(v, int | float):
                out[k] = _clamp(v)
        # Gemini가 scene_issues를 null로 반환할 수 있음
        if out.get("scene_issues") is None:
            out["scene_issues"] = []
        return out


# -- Unified Review (Phase 13-A) --


class TechnicalEvaluation(BaseModel):
    """규칙 기반 검증 결과 + Gemini 기술 평가."""

    overall_score: float = 0.0
    passed: bool = True
    feedback: str = ""
    scene_issues: list[dict] = []


class ReflectionOutput(BaseModel):
    """Self-Reflection 결과 (근본 원인 분석 + 수정 전략)."""

    root_cause: str = ""
    impact: str = ""
    strategy: str = ""
    expected_outcome: str = ""


class UnifiedReviewOutput(BaseModel):
    """통합 Review 응답: 기술 + 서사 + 리플렉션을 단일 호출로."""

    technical: TechnicalEvaluation
    narrative: NarrativeScoreOutput
    reflection: ReflectionOutput | None = None


# -- Writer Plan --


class LocationPlan(BaseModel):
    """Location Map 항목 (장소 이름 + 해당 씬 + 환경 태그).

    Phase 18 Stage Workflow에서도 공유하는 모델.
    WriterPlan.locations 타입 힌트 + Gemini 출력 검증 양쪽에서 사용.
    """

    name: str = ""
    scenes: list[int] = []
    tags: list[str] = []


# Backward compat alias
LocationEntryOutput = LocationPlan


class WriterPlanOutput(BaseModel):
    """Writer Planning Step의 LLM 응답."""

    hook_strategy: str = ""
    emotional_arc: list[str] = []
    scene_distribution: dict[str, int] = {}
    locations: list[LocationEntryOutput] = []

    @field_validator("hook_strategy", mode="before")
    @classmethod
    def _coerce_hook_strategy(cls, v: object) -> str:
        """Gemini가 dict로 반환하는 경우 JSON string으로 변환."""
        if isinstance(v, dict):
            import json

            return json.dumps(v, ensure_ascii=False)
        return str(v) if v else ""


# -- Helper --


def validate_with_model(model_class: type[BaseModel], data: dict | list | str) -> QCResult:
    """Pydantic 검증 → QCResult 변환.

    validate_fn 시그니처:  (data) -> {"ok": bool, "issues": [...], "checks": {...}}
    """
    if not isinstance(data, dict):
        return QCResult(ok=False, issues=["Response must be a JSON object"])
    try:
        model_class.model_validate(data)
        return QCResult(ok=True)
    except ValidationError as e:
        issues = [str(err) for err in e.errors()]
        return QCResult(ok=False, issues=issues)
