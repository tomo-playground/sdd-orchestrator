from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class VoicePreset(Base, TimestampMixin):
    """Reusable voice preset for TTS rendering."""

    __tablename__ = "voice_presets"

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

    @property
    def audio_url(self) -> str | None:
        if not self.audio_asset_id:
            return None
        from database import get_db
        from models.media_asset import MediaAsset
        db = next(get_db())
        try:
            asset = db.get(MediaAsset, self.audio_asset_id)
            return asset.url if asset else None
        finally:
            db.close()
