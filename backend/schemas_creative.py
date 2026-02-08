"""Pydantic schemas for the Creative Engine module."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

VALID_TASK_TYPES = Literal["scenario", "dialogue", "visual_concept", "character_design"]

# ── Common ────────────────────────────────────────────────────


class OkResponse(BaseModel):
    ok: bool = True


# ── Shared sub-schemas ───────────────────────────────────────


class CriterionWeight(BaseModel):
    """Single evaluation criterion with weight and description."""

    weight: float
    description: str


class TokenUsage(BaseModel):
    """LLM token usage counters."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AgentConfigItem(BaseModel):
    """Agent slot in a session's agent_config array."""

    preset_id: int | None = None
    role: str | None = None
    role_override: str | None = None


# ── Agent Presets ─────────────────────────────────────────────


class AgentPresetCreate(BaseModel):
    name: str
    role_description: str
    system_prompt: str
    model_provider: str = "gemini"
    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.9
    is_system: bool = False


class AgentPresetUpdate(BaseModel):
    name: str | None = None
    role_description: str | None = None
    system_prompt: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None


class AgentPresetResponse(BaseModel):
    id: int
    name: str
    role_description: str
    system_prompt: str
    model_provider: str
    model_name: str
    temperature: float
    is_system: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Creative Sessions ────────────────────────────────────────


class CreativeSessionCreate(BaseModel):
    task_type: VALID_TASK_TYPES = "scenario"
    objective: str
    evaluation_criteria: dict[str, CriterionWeight] | None = None
    character_id: int | None = None
    context: dict[str, Any] | None = None
    agent_config: list[AgentConfigItem] | None = None
    max_rounds: int = 3


class CreativeSessionResponse(BaseModel):
    id: int
    task_type: str
    objective: str
    evaluation_criteria: dict[str, Any] | None = None
    character_id: int | None = None
    context: dict[str, Any] | None = None
    agent_config: list[dict[str, Any]] | None = None
    final_output: dict[str, Any] | None = None
    max_rounds: int
    total_token_usage: TokenUsage | None = None
    status: str
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
    diff_summary: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TraceTimelineResponse(BaseModel):
    """Full session timeline with rounds and traces."""

    session: CreativeSessionResponse
    rounds: list[CreativeRoundResponse]
    traces: list[CreativeTraceResponse]


# ── Actions ──────────────────────────────────────────────────


class RunRoundRequest(BaseModel):
    """Optional overrides for a round execution."""

    feedback: str | None = None  # User feedback to incorporate


class FinalizeRequest(BaseModel):
    """Select the final output."""

    selected_output: dict[str, Any]  # The chosen result
    reason: str | None = None


# ── Task Types ──────────────────────────────────────────────


class TaskTypeItem(BaseModel):
    key: str
    label: str
    description: str


class TaskTypeListResponse(BaseModel):
    items: list[TaskTypeItem]
