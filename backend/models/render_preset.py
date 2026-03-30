from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class RenderPreset(Base, TimestampMixin):
    """Reusable render settings preset."""

    __tablename__ = "render_presets"
    __table_args__ = (CheckConstraint("bgm_mode IN ('manual', 'auto')", name="ck_render_presets_bgm_mode"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)

    # Render fields
    bgm_file: Mapped[str | None] = mapped_column(String(255))
    bgm_volume: Mapped[float | None] = mapped_column(Float)
    audio_ducking: Mapped[bool | None] = mapped_column(Boolean)
    scene_text_font: Mapped[str | None] = mapped_column(String(255))
    layout_style: Mapped[str | None] = mapped_column(String(50))
    frame_style: Mapped[str | None] = mapped_column(String(255))
    transition_type: Mapped[str | None] = mapped_column(String(50))
    ken_burns_preset: Mapped[str | None] = mapped_column(String(50))
    ken_burns_intensity: Mapped[float | None] = mapped_column(Float)
    speed_multiplier: Mapped[float | None] = mapped_column(Float)
    bgm_mode: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")  # "manual" | "auto"
    music_preset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("music_presets.id", ondelete="SET NULL"), nullable=True
    )
