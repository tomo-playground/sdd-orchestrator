from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project
    from models.render_preset import RenderPreset
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

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="groups")
    render_preset: Mapped[RenderPreset | None] = relationship("RenderPreset", lazy="joined")
    storyboards: Mapped[list[Storyboard]] = relationship("Storyboard", back_populates="group")
