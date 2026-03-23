"""Unified Activity Log model for generation history and favorites."""

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class ActivityLog(Base, TimestampMixin):
    """Unified store for all generation events and saved (favorite) prompts."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Context
    storyboard_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("storyboards.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scene_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scenes.id", ondelete="SET NULL"), index=True)
    character_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="SET NULL"), index=True
    )

    # The Prompt Bundle
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    sd_params: Mapped[dict | None] = mapped_column(JSONB)  # steps, cfg, sampler, etc.
    seed: Mapped[int | None] = mapped_column(BigInteger)

    # Results & Quality - media_asset reference (normalized)
    media_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    media_asset = relationship("MediaAsset", lazy="joined")

    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    tags_used: Mapped[list[str] | None] = mapped_column(JSONB)

    @property
    def image_url(self) -> str | None:
        """Generate URL from media_asset reference."""
        return self.media_asset.url if self.media_asset else None

    # Status
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, fail
