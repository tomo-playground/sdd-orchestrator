"""GroupConfig model — separated config for groups (1:1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.character import Character
    from models.group import Group
    from models.render_preset import RenderPreset
    from models.sd_model import StyleProfile
    from models.voice_preset import VoicePreset


class GroupConfig(Base, TimestampMixin):
    """Separated configuration for a Group (1:1 relationship).

    Follows the DB Schema Design Principle: content tables != config tables.
    Cascade order: System Default < Project < GroupConfig < Storyboard.
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
    default_character_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="SET NULL"),
    )
    default_style_profile_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("style_profiles.id", ondelete="SET NULL"),
    )
    narrator_voice_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("voice_presets.id", ondelete="SET NULL"),
    )
    language: Mapped[str | None] = mapped_column(String(20))
    structure: Mapped[str | None] = mapped_column(String(30))
    duration: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    group: Mapped[Group] = relationship(
        "Group",
        back_populates="config",
    )
    render_preset: Mapped[RenderPreset | None] = relationship(
        "RenderPreset",
        lazy="joined",
    )
    default_character: Mapped[Character | None] = relationship(
        "Character",
        foreign_keys=[default_character_id],
    )
    default_style_profile: Mapped[StyleProfile | None] = relationship(
        "StyleProfile",
        foreign_keys=[default_style_profile_id],
    )
    narrator_voice_preset: Mapped[VoicePreset | None] = relationship(
        "VoicePreset",
        foreign_keys=[narrator_voice_preset_id],
    )
