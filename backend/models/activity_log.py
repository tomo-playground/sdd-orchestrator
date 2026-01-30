"""Unified Activity Log model for generation history and favorites."""

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class ActivityLog(Base, TimestampMixin):
    """Unified store for all generation events and saved (favorite) prompts."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Context
    storyboard_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("storyboards.id"), index=True)
    scene_id: Mapped[int | None] = mapped_column(Integer, index=True)
    character_id: Mapped[int | None] = mapped_column(Integer, index=True)

    # The Prompt Bundle
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    sd_params: Mapped[dict | None] = mapped_column(JSONB) # steps, cfg, sampler, etc.
    seed: Mapped[int | None] = mapped_column(BigInteger)

    # Results & Quality
    image_url: Mapped[str | None] = mapped_column(String(500))
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    tags_used: Mapped[list[str] | None] = mapped_column(JSONB)

    # Status & Management
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="success") # success, fail
    name: Mapped[str | None] = mapped_column(String(200)) # Human-readable name if favorited
