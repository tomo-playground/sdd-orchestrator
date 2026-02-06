from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.media_asset import MediaAsset


class Project(Base, TimestampMixin):
    """A YouTube Channel project that holds multiple content groups."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Metadata for the channel/project
    handle: Mapped[str | None] = mapped_column(String(100))  # e.g. @MyChannel
    avatar_media_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    avatar_media_asset: Mapped[MediaAsset | None] = relationship(
        foreign_keys=[avatar_media_asset_id],
    )

    @property
    def avatar_url(self) -> str | None:
        if self.avatar_media_asset:
            return self.avatar_media_asset.url
        return None

    @property
    def avatar_key(self) -> str | None:
        """Storage key for avatar (for video rendering)."""
        if self.avatar_media_asset:
            return self.avatar_media_asset.storage_key
        return None

    # Relationships
    groups: Mapped[list[Group]] = relationship("Group", back_populates="project", cascade="all, delete-orphan")
