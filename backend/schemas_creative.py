"""Pydantic schemas for the Creative Lab module."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Common ────────────────────────────────────────────────────


class OkResponse(BaseModel):
    ok: bool = True


# ── Shared sub-schemas ───────────────────────────────────────


class TokenUsage(BaseModel):
    """LLM token usage counters."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# ── Agent Presets ─────────────────────────────────────────────


class AgentPresetCreate(BaseModel):
    name: str
    role_description: str
    system_prompt: str
    model_provider: str = "gemini"
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.9
    is_system: bool = False
    agent_role: str | None = None
    category: str | None = None
    agent_metadata: dict[str, Any] | None = None


class AgentPresetUpdate(BaseModel):
    name: str | None = None
    role_description: str | None = None
    system_prompt: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    agent_role: str | None = None
    category: str | None = None
    agent_metadata: dict[str, Any] | None = None


class AgentPresetResponse(BaseModel):
    id: int
    name: str
    role_description: str
    system_prompt: str
    model_provider: str
    model_name: str
    temperature: float
    is_system: bool
    agent_role: str | None = None
    category: str | None = None
    agent_metadata: dict[str, Any] | None = None
    template_content: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryOption(BaseModel):
    value: str
    label: str


class AgentPresetsListResponse(BaseModel):
    presets: list[AgentPresetResponse]
    categories: list[CategoryOption]


# ── Creative Sessions ────────────────────────────────────────


class CreativeSessionResponse(BaseModel):
    id: int
    objective: str
    evaluation_criteria: dict[str, Any] | None = None
    character_id: int | None = None
    context: dict[str, Any] | None = None
    agent_config: list[dict[str, Any]] | None = None
    final_output: dict[str, Any] | None = None
    max_rounds: int
    total_token_usage: TokenUsage | None = None
    status: str
    session_type: str | None = "shorts"
    director_mode: str | None = "advisor"
    concept_candidates: dict[str, Any] | None = None
    selected_concept_index: int | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CreativeSessionListResponse(BaseModel):
    items: list[CreativeSessionResponse]
    total: int


# ── Rounds ───────────────────────────────────────────────────


class CreativeRoundResponse(BaseModel):
    id: int
    session_id: int
    round_number: int
    leader_summary: str | None = None
    round_decision: str | None = None
    best_agent_role: str | None = None
    best_score: float | None = None
    leader_direction: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Traces ───────────────────────────────────────────────────


class CreativeTraceResponse(BaseModel):
    id: int
    session_id: int
    round_number: int
    sequence: int
    trace_type: str
    agent_role: str
    agent_preset_id: int | None = None
    input_prompt: str
    output_content: str
    score: float | None = None
    feedback: str | None = None
    model_id: str
    token_usage: dict[str, Any] | None = None
    latency_ms: int
    temperature: float
    parent_trace_id: int | None = None
    phase: str | None = None
    step_name: str | None = None
    target_agent: str | None = None
    decision_context: dict[str, Any] | None = None
    retry_count: int = 0
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TraceTimelineResponse(BaseModel):
    """Full session timeline with rounds and traces."""

    session: CreativeSessionResponse
    rounds: list[CreativeRoundResponse]
    traces: list[CreativeTraceResponse]


# ── Actions ──────────────────────────────────────────────────


# ── Shorts Pipeline ─────────────────────────────────────────


class ShortsSessionCreate(BaseModel):
    """Create a V2 shorts pipeline session."""

    topic: str
    duration: int = 30
    structure: str = "Monologue"
    language: str = "Korean"
    character_id: int | None = None
    character_ids: dict[str, int] | None = None  # {"A": 1, "B": 2}
    director_mode: str = "advisor"
    max_rounds: int = 2
    references: list[str] | None = None
    material_urls: list[str] | None = None
    disabled_steps: list[str] | None = None


class SelectConceptRequest(BaseModel):
    """Select a concept from Phase 1 candidates."""

    concept_index: int


class RetrySessionRequest(BaseModel):
    """Retry a failed session."""

    mode: str = "resume"  # "resume" | "restart"


class SendToStudioRequest(BaseModel):
    """Send completed scenes to Studio as a storyboard."""

    group_id: int
    title: str | None = None
    deep_parse: bool = False


class SendToStudioResponse(BaseModel):
    """Response after sending to Studio."""

    storyboard_id: int
    scene_count: int


class PipelineStatusResponse(BaseModel):
    """Lightweight status for polling."""

    status: str
    session_type: str
    progress: dict[str, Any] | None = None
    concept_candidates: dict[str, Any] | None = None
    selected_concept_index: int | None = None


# ── Interactive Review ──────────────────────────────────────


class QCIssue(BaseModel):
    """Single QC issue — fields are str (not Literal) because Gemini output varies."""

    severity: str  # expected: "critical" | "warning" | "suggestion"
    category: str  # expected: "readability" | "hook" | "emotion" | "tts" | "diversity" | "consistency"
    scene: int | str  # scene index or "all"
    description: str

    model_config = ConfigDict(extra="ignore")


class QCAnalysis(BaseModel):
    """QC analysis result from Gemini — lenient parsing for LLM output."""

    overall_rating: str = "unknown"  # expected: "good" | "needs_revision" | "poor"
    score: float = 0.0
    score_breakdown: dict[str, float] = {}
    summary: str = ""
    issues: list[QCIssue] = []
    strengths: list[str] = []
    revision_suggestions: list[str] = []

    model_config = ConfigDict(extra="ignore")


class ReviewMessage(BaseModel):
    role: str  # expected: "system" | "user" | "agent"
    content: str
    timestamp: str

    model_config = ConfigDict(extra="ignore")


class StepReviewResponse(BaseModel):
    step: str
    result: dict[str, Any] | None = None
    qc_analysis: QCAnalysis | None = None
    messages: list[ReviewMessage] = []


class ReviewMessageRequest(BaseModel):
    message: str = Field(..., max_length=2000)

    model_config = ConfigDict(json_schema_extra={"example": {"message": "씬 3의 대사가 어색해요"}})


class ReviewActionRequest(BaseModel):
    action: Literal["approve", "revise"]
    feedback: str | None = None
