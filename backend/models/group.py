from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project


class Group(Base, TimestampMixin):
    """A series or category of content within a project/channel."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Default settings for this series/group
    default_bgm_file: Mapped[str | None] = mapped_column(String(255))
    default_narrator_voice: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="groups")
