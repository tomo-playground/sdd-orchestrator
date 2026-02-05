"""Storyboard model for managing YouTube Shorts projects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.render_history import RenderHistory
    from models.scene import Scene
    from models.storyboard_character import StoryboardCharacter


class Storyboard(Base, TimestampMixin, SoftDeleteMixin):
    """An individual video content (Episode) within a series/group."""

    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)

    @property
    def video_url(self) -> str | None:
        if self.render_history:
            return self.render_history[0].media_asset.url
        return None

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="storyboards")
    scenes: Mapped[list[Scene]] = relationship("Scene", back_populates="storyboard", cascade="all, delete-orphan")
    characters: Mapped[list[StoryboardCharacter]] = relationship(
        "StoryboardCharacter", back_populates="storyboard", cascade="all, delete-orphan"
    )
    render_history: Mapped[list[RenderHistory]] = relationship(
        "RenderHistory",
        back_populates="storyboard",
        cascade="all, delete-orphan",
        order_by="desc(RenderHistory.created_at)",
    )
