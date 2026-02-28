"""GroupConfig model — separated config for groups (1:1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.render_preset import RenderPreset
    from models.sd_model import StyleProfile
    from models.voice_preset import VoicePreset


class GroupConfig(Base, TimestampMixin):
    """Separated configuration for a Group (1:1 relationship).

    Follows the DB Schema Design Principle: content tables != config tables.
    Cascade order: System Default < GroupConfig (2-level).
    """

    __tablename__ = "group_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Config fields (override project-level defaults)
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
    language: Mapped[str | None] = mapped_column(String(20))
    duration: Mapped[int | None] = mapped_column(Integer)

    # SD generation settings (migrated from scenes)
    sd_steps: Mapped[int | None] = mapped_column(Integer)
    sd_cfg_scale: Mapped[float | None] = mapped_column(Float)
    sd_sampler_name: Mapped[str | None] = mapped_column(String(50))
    sd_clip_skip: Mapped[int | None] = mapped_column(Integer)

    # Channel DNA (tone, audience, worldview, guidelines)
    channel_dna: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    group: Mapped[Group] = relationship(
        "Group",
        back_populates="config",
    )
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
