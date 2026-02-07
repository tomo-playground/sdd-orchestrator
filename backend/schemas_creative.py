"""Pydantic schemas for the Creative Engine module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ── Common ────────────────────────────────────────────────────


class OkResponse(BaseModel):
    ok: bool = True


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
    task_type: str = "scenario"
    objective: str
    evaluation_criteria: dict | None = None
    character_id: int | None = None
    context: dict | None = None
    agent_config: list[dict] | None = None  # [{preset_id, role_override}]
    max_rounds: int = 3


class CreativeSessionResponse(BaseModel):
    id: int
    task_type: str
    objective: str
    evaluation_criteria: dict | None = None
    character_id: int | None = None
    context: dict | None = None
    agent_config: list[dict] | None = None
    final_output: dict | None = None
    max_rounds: int
    total_token_usage: dict | None = None
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
    token_usage: dict | None = None
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

    selected_output: dict  # The chosen result
    reason: str | None = None


class SendToStudioRequest(BaseModel):
    """Send creative output to Studio as storyboard scenes."""

    storyboard_id: int | None = None  # Existing storyboard, or create new
    group_id: int = 1


class SendToStudioResponse(BaseModel):
    storyboard_id: int
    scenes_created: int
