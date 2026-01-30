"""Evaluation models for mode A/B quality comparison."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class EvaluationRun(Base, TimestampMixin):
    """Tracks a single evaluation generation and validation result."""

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str | None] = mapped_column(String(50), index=True)

    test_name: Mapped[str] = mapped_column(String(100), index=True)
    mode: Mapped[str] = mapped_column(String(20), index=True)  # standard, lora

    # Character context
    character_id: Mapped[int | None] = mapped_column(Integer, index=True)
    character_name: Mapped[str | None] = mapped_column(String(100))

    # Generation Data
    prompt_used: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    seed: Mapped[int | None] = mapped_column(Integer)
    steps: Mapped[int] = mapped_column(Integer, default=20)
    cfg_scale: Mapped[float] = mapped_column(Float, default=7.0)

    # Validation Result
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    matched_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    missing_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    extra_tags: Mapped[list[str] | None] = mapped_column(JSONB)
