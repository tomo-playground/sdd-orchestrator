"""Evaluation model for Mode A/B comparison testing."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class EvaluationRun(Base, TimestampMixin):
    """Single evaluation run result for Mode A/B comparison."""

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Test identification
    test_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # "standard" or "lora"

    # Character context
    character_id: Mapped[int | None] = mapped_column(Integer, index=True)
    character_name: Mapped[str | None] = mapped_column(String(100))

    # Prompt used
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text)

    # WD14 validation results
    match_rate: Mapped[float | None] = mapped_column(Float)
    matched_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    missing_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    extra_tags: Mapped[list[str] | None] = mapped_column(JSONB)

    # Generation details
    image_path: Mapped[str | None] = mapped_column(String(500))
    seed: Mapped[int | None] = mapped_column(Integer)
    steps: Mapped[int | None] = mapped_column(Integer)
    cfg_scale: Mapped[float | None] = mapped_column(Float)

    # Batch tracking
    batch_id: Mapped[str | None] = mapped_column(String(50), index=True)
    # Groups runs from same evaluation session
