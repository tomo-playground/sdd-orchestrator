"""Storyboard model for managing YouTube Shorts projects."""

from typing import List
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Storyboard(Base, TimestampMixin):
    """A YouTube Shorts project containing multiple scenes."""

    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Project-level defaults
    default_character_id: Mapped[int | None] = mapped_column(Integer)
    default_style_profile_id: Mapped[int | None] = mapped_column(Integer)
    
    # Relationship to scenes
    scenes: Mapped[List["Scene"]] = relationship("Scene", backref="storyboard", cascade="all, delete-orphan")
