from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset


class VoicePreset(Base, TimestampMixin):
    """Reusable voice preset for TTS rendering."""

    __tablename__ = "voice_presets"
    __table_args__ = (CheckConstraint("source_type IN ('generated', 'uploaded')", name="ck_voice_presets_source_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "generated"
    tts_engine: Mapped[str | None] = mapped_column(String(20))
    audio_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    voice_design_prompt: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default="korean")
    sample_text: Mapped[str | None] = mapped_column(Text)
    voice_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    audio_asset: Mapped[MediaAsset | None] = relationship("MediaAsset", foreign_keys=[audio_asset_id])

    @property
    def audio_url(self) -> str | None:
        if self.audio_asset is None:
            return None
        return self.audio_asset.url
