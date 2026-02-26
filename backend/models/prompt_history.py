"""Prompt History model for V3 Schema."""

from sqlalchemy import BigInteger, Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, SoftDeleteMixin, TimestampMixin


class PromptHistory(Base, TimestampMixin, SoftDeleteMixin):
    """Stores generated prompt results and their quality metrics."""

    __tablename__ = "prompt_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200))
    character_id: Mapped[int | None] = mapped_column(Integer, index=True)

    # Prompt Data
    positive_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text)

    # Generation Settings
    steps: Mapped[int] = mapped_column(Integer, default=20)
    cfg_scale: Mapped[float] = mapped_column(Float, default=7.0)
    sampler_name: Mapped[str | None] = mapped_column(String(50))
    seed: Mapped[int | None] = mapped_column(BigInteger)
    clip_skip: Mapped[int] = mapped_column(Integer, default=2)

    # Bundles
    lora_settings: Mapped[list[dict] | None] = mapped_column(JSONB)
    context_tags: Mapped[list[str] | None] = mapped_column(JSONB)

    # Usage & Status
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    use_count: Mapped[int] = mapped_column(Integer, default=1)

    # Quality Metrics
    last_match_rate: Mapped[float | None] = mapped_column(Float)
    avg_match_rate: Mapped[float | None] = mapped_column(Float)
    validation_count: Mapped[int] = mapped_column(Integer, default=0)
