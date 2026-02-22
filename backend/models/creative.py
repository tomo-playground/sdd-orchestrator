"""Creative Engine models for multi-agent creative sessions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.character import Character


class CreativeAgentPreset(Base, TimestampMixin, SoftDeleteMixin):
    """Reusable agent persona preset with model configuration."""

    __tablename__ = "creative_agent_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    role_description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(20), nullable=False)  # gemini | ollama
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.9)
    is_system: Mapped[bool] = mapped_column(default=False, server_default="false")
    agent_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    agent_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    traces: Mapped[list[CreativeTrace]] = relationship("CreativeTrace", back_populates="agent_preset")


class CreativeSession(Base, TimestampMixin, SoftDeleteMixin):
    """A creative generation session orchestrated by a leader agent."""

    __tablename__ = "creative_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    character_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    context: Mapped[dict | None] = mapped_column(JSONB)
    agent_config: Mapped[list[dict] | None] = mapped_column(JSONB)
    final_output: Mapped[dict | None] = mapped_column(JSONB)
    max_rounds: Mapped[int] = mapped_column(Integer, default=3)
    total_token_usage: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    session_type: Mapped[str] = mapped_column(String(20), server_default="shorts", nullable=False)
    director_mode: Mapped[str] = mapped_column(String(20), server_default="advisor", nullable=False)
    concept_candidates: Mapped[dict | None] = mapped_column(JSONB)
    selected_concept_index: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    character: Mapped[Character | None] = relationship("Character", foreign_keys=[character_id])
    rounds: Mapped[list[CreativeSessionRound]] = relationship(
        "CreativeSessionRound", back_populates="session", cascade="all, delete-orphan"
    )
    traces: Mapped[list[CreativeTrace]] = relationship(
        "CreativeTrace", back_populates="session", cascade="all, delete-orphan"
    )


class CreativeSessionRound(Base):
    """Summary of a single deliberation round within a session."""

    __tablename__ = "creative_session_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creative_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    leader_summary: Mapped[str] = mapped_column(Text, nullable=False)
    round_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    best_agent_role: Mapped[str | None] = mapped_column(String(50))
    best_score: Mapped[float | None] = mapped_column(Float)
    leader_direction: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    session: Mapped[CreativeSession] = relationship("CreativeSession", back_populates="rounds")


class CreativeTrace(Base):
    """Individual LLM call trace within a session round."""

    __tablename__ = "creative_traces"
    __table_args__ = (
        Index("ix_creative_traces_session_round_seq", "session_id", "round_number", "sequence"),
        Index("ix_creative_traces_session_type", "session_id", "trace_type"),
        Index("ix_creative_traces_session_role", "session_id", "agent_role"),
        Index("ix_creative_traces_phase_step", "session_id", "phase", "step_name"),
        Index("ix_creative_traces_target", "session_id", "target_agent"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_type: Mapped[str] = mapped_column(String(20), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_preset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("creative_agent_presets.id", ondelete="SET NULL"), nullable=True
    )
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_content: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    token_usage: Mapped[dict | None] = mapped_column(JSONB)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    parent_trace_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("creative_traces.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    # V2 fields
    phase: Mapped[str | None] = mapped_column(String(20))
    step_name: Mapped[str | None] = mapped_column(String(50))
    target_agent: Mapped[str | None] = mapped_column(String(50))
    decision_context: Mapped[dict | None] = mapped_column(JSONB)
    retry_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    # Relationships
    session: Mapped[CreativeSession] = relationship("CreativeSession", back_populates="traces")
    agent_preset: Mapped[CreativeAgentPreset | None] = relationship("CreativeAgentPreset", back_populates="traces")
    parent_trace: Mapped[CreativeTrace | None] = relationship(
        "CreativeTrace", remote_side=[id], foreign_keys=[parent_trace_id]
    )
