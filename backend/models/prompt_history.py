"""Prompt history model for saving successful prompts."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class PromptHistory(Base, TimestampMixin):
    """Saved prompt with settings for reuse."""

    __tablename__ = "prompt_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    positive_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text)

    # Generation settings
    steps: Mapped[int | None] = mapped_column(Integer)
    cfg_scale: Mapped[float | None] = mapped_column(Float)
    sampler_name: Mapped[str | None] = mapped_column(String(100))
    seed: Mapped[int | None] = mapped_column(Integer)
    clip_skip: Mapped[int | None] = mapped_column(Integer)

    # Character and LoRA
    character_id: Mapped[int | None] = mapped_column(Integer, index=True)
    lora_settings: Mapped[list[dict] | None] = mapped_column(JSONB)
    # [{"lora_id": 1, "name": "xxx", "weight": 0.7}, ...]

    # Context tags
    context_tags: Mapped[dict | None] = mapped_column(JSONB)
    # {"expression": ["smile"], "pose": ["standing"], ...}

    # WD14 validation scores
    last_match_rate: Mapped[float | None] = mapped_column(Float)
    avg_match_rate: Mapped[float | None] = mapped_column(Float)
    validation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    preview_image_url: Mapped[str | None] = mapped_column(String(500))
