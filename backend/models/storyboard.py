"""Storyboard model for managing YouTube Shorts projects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.scene import Scene


class Storyboard(Base, TimestampMixin):
    """An individual video content (Episode) within a series/group."""

    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Project-level defaults
    default_character_id: Mapped[int | None] = mapped_column(Integer)
    default_style_profile_id: Mapped[int | None] = mapped_column(Integer)

    # Results
    video_url: Mapped[str | None] = mapped_column(String(500))
    recent_videos_json: Mapped[str | None] = mapped_column(Text)  # JSON string of recent videos

    # Relationships
    scenes: Mapped[list[Scene]] = relationship("Scene", back_populates="storyboard", cascade="all, delete-orphan")
