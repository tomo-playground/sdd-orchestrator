from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project
    from models.render_preset import RenderPreset
    from models.sd_model import StyleProfile
    from models.storyboard import Storyboard
    from models.voice_preset import VoicePreset


class Group(Base, TimestampMixin):
    """A series or category of content within a project/channel."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Config fields (previously in group_config table)
    render_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("render_presets.id", ondelete="SET NULL"),
    )
    style_profile_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("style_profiles.id", ondelete="SET NULL"),
    )
    narrator_voice_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("voice_presets.id", ondelete="SET NULL"),
    )
    channel_dna: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="groups")
    storyboards: Mapped[list[Storyboard]] = relationship("Storyboard", back_populates="group")
    render_preset: Mapped[RenderPreset | None] = relationship(
        "RenderPreset",
        lazy="joined",
    )
    style_profile: Mapped[StyleProfile | None] = relationship(
        "StyleProfile",
        foreign_keys=[style_profile_id],
    )
    narrator_voice_preset: Mapped[VoicePreset | None] = relationship(
        "VoicePreset",
        foreign_keys=[narrator_voice_preset_id],
    )

    # Response-only: derived from relationships
    @property
    def render_preset_name(self) -> str | None:
        return self.render_preset.name if self.render_preset else None

    @property
    def style_profile_name(self) -> str | None:
        return self.style_profile.name if self.style_profile else None

    @property
    def voice_preset_name(self) -> str | None:
        return self.narrator_voice_preset.name if self.narrator_voice_preset else None
