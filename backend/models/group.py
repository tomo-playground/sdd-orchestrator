from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project
    from models.render_preset import RenderPreset
    from models.sd_model import StyleProfile
    from models.storyboard import Storyboard


class Group(Base, TimestampMixin):
    """A series or category of content within a project/channel."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Render preset reference (A안: 참조만)
    render_preset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("render_presets.id", ondelete="SET NULL"), nullable=True
    )

    # Cascading config defaults (override project-level)
    default_character_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="SET NULL"),
    )
    default_style_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("style_profiles.id", ondelete="SET NULL"),
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="groups")
    render_preset: Mapped[RenderPreset | None] = relationship("RenderPreset", lazy="joined")
    default_character: Mapped[object | None] = relationship("Character", foreign_keys=[default_character_id])
    default_style_profile: Mapped[StyleProfile | None] = relationship("StyleProfile", foreign_keys=[default_style_profile_id])
    storyboards: Mapped[list[Storyboard]] = relationship("Storyboard", back_populates="group")
