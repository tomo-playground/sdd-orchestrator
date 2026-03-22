"""Storyboard model for managing YouTube Shorts projects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config import DEFAULT_STRUCTURE, DEFAULT_TONE
from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.media_asset import MediaAsset
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
    structure: Mapped[str] = mapped_column(String(50), nullable=False, default=DEFAULT_STRUCTURE)
    tone: Mapped[str] = mapped_column(String(30), nullable=False, default=DEFAULT_TONE, server_default=DEFAULT_TONE)
    duration: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Phase 12-C: AI BGM Pipeline
    bgm_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    bgm_mood: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Seed Anchoring: base seed for consistent scene generation
    base_seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    bgm_audio_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )

    # Phase 18: Stage Workflow
    stage_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Phase 20-C: Casting recommendation (optgroup, structure badge, etc.)
    casting_recommendation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    @property
    def video_url(self) -> str | None:
        if self.render_history and self.render_history[0].media_asset:
            return self.render_history[0].media_asset.url
        return None

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="storyboards")
    scenes: Mapped[list[Scene]] = relationship(
        "Scene", back_populates="storyboard", cascade="all, delete-orphan", order_by="Scene.order"
    )
    characters: Mapped[list[StoryboardCharacter]] = relationship(
        "StoryboardCharacter", back_populates="storyboard", cascade="all, delete-orphan"
    )
    render_history: Mapped[list[RenderHistory]] = relationship(
        "RenderHistory",
        back_populates="storyboard",
        cascade="all, delete-orphan",
        order_by="desc(RenderHistory.created_at)",
    )
    bgm_audio_asset: Mapped[MediaAsset | None] = relationship(
        "MediaAsset", foreign_keys=[bgm_audio_asset_id], lazy="joined"
    )
