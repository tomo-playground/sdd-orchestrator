"""RenderHistory model for tracking video render outputs per storyboard."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset
    from models.storyboard import Storyboard


class RenderHistory(Base, TimestampMixin):
    """One row per rendered video, linked to a storyboard and its media asset."""

    __tablename__ = "render_history"
    __table_args__ = (Index("ix_render_history_sb_created", "storyboard_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storyboard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("storyboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(20), nullable=False)

    # YouTube upload tracking
    youtube_video_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    youtube_upload_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    youtube_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    storyboard: Mapped[Storyboard] = relationship("Storyboard", back_populates="render_history")
    media_asset: Mapped[MediaAsset] = relationship("MediaAsset", foreign_keys=[media_asset_id])
