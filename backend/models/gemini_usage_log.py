"""Gemini usage log model for tracking image editing costs and effectiveness."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class GeminiUsageLog(Base, TimestampMixin):
    """Gemini Nano Banana usage log for cost tracking and analytics."""

    __tablename__ = "gemini_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Session tracking
    project_name: Mapped[str | None] = mapped_column(String(200), index=True)
    scene_index: Mapped[int | None] = mapped_column(Integer, index=True)

    # Edit metadata
    edit_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # pose, expression, gaze, framing, hands
    original_prompt: Mapped[str | None] = mapped_column(Text)
    target_change: Mapped[str] = mapped_column(Text, nullable=False)

    # Results
    before_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    after_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    preserve_elements: Mapped[list[str] | None] = mapped_column(JSONB)

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Success metrics
    match_rate_before: Mapped[float | None] = mapped_column(Float)
    match_rate_after: Mapped[float | None] = mapped_column(Float)
    improvement: Mapped[float | None] = mapped_column(Float)  # after - before

    # Analysis data
    vision_analysis: Mapped[dict | None] = mapped_column(JSONB)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed", index=True
    )  # completed, error
    error_message: Mapped[str | None] = mapped_column(Text)
