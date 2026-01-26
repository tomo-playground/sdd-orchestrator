"""Scene quality score model for tracking Match Rate per scene."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class SceneQualityScore(Base, TimestampMixin):
    """Scene quality score tracking."""

    __tablename__ = "scene_quality_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    scene_id: Mapped[int | None] = mapped_column(Integer, index=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    prompt: Mapped[str | None] = mapped_column(Text)

    # Quality metrics
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    matched_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    missing_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    extra_tags: Mapped[list[str] | None] = mapped_column(JSONB)

    # Validation timestamp
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)
