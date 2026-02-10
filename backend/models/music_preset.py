from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset


class MusicPreset(Base, TimestampMixin):
    """Reusable AI-generated music preset for BGM."""

    __tablename__ = "music_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    prompt: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[float | None] = mapped_column(Float)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    audio_asset: Mapped[MediaAsset | None] = relationship("MediaAsset", foreign_keys=[audio_asset_id])
