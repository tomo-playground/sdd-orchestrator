"""Generation log model for tracking prompt generation metadata and success patterns."""

from sqlalchemy import BigInteger, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class GenerationLog(Base, TimestampMixin):
    """Generation log for analytics and pattern learning."""

    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    scene_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Generation data
    prompt: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSONB)  # List of tags used
    sd_params: Mapped[dict | None] = mapped_column(JSONB)  # SD parameters (steps, cfg_scale, etc.)

    # Quality metrics
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    seed: Mapped[int | None] = mapped_column(BigInteger)

    # Status tracking
    status: Mapped[str | None] = mapped_column(String(20), index=True)  # success, fail, pending
    image_url: Mapped[str | None] = mapped_column(Text)
