"""Storyboard model for managing YouTube Shorts projects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.media_asset import MediaAsset
    from models.scene import Scene


class Storyboard(Base, TimestampMixin):
    """An individual video content (Episode) within a series/group."""

    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Project-level defaults
    default_character_id: Mapped[int | None] = mapped_column(Integer)
    default_style_profile_id: Mapped[int | None] = mapped_column(Integer)
    default_caption: Mapped[str | None] = mapped_column(Text)

    # Results
    # video_url column removed
    video_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    video_asset: Mapped[MediaAsset | None] = relationship(
        foreign_keys=[video_asset_id],
    )

    @property
    def video_url(self) -> str | None:
        if self.video_asset:
            return self.video_asset.url
        return None

    recent_videos_json: Mapped[str | None] = mapped_column(Text)  # JSON string of recent videos

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="storyboards")
    scenes: Mapped[list[Scene]] = relationship("Scene", back_populates="storyboard", cascade="all, delete-orphan")
