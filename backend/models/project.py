from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.media_asset import MediaAsset
    from models.render_preset import RenderPreset
    from models.sd_model import StyleProfile


class Project(Base, TimestampMixin):
    """A YouTube Channel project that holds multiple content groups."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # avatar_url column removed
    avatar_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    avatar_asset: Mapped[MediaAsset] = relationship(
        foreign_keys=[avatar_asset_id],
    )

    @property
    def avatar_url(self) -> str | None:
        if self.avatar_asset:
            return self.avatar_asset.url
        return None

    # Metadata for the channel/project
    handle: Mapped[str | None] = mapped_column(String(100)) # e.g. @MyChannel
    avatar_key: Mapped[str | None] = mapped_column(String(100))

    # Cascading config defaults
    render_preset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("render_presets.id", ondelete="SET NULL"),
    )
    character_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="SET NULL"),
    )
    style_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("style_profiles.id", ondelete="SET NULL"),
    )

    # Relationships
    groups: Mapped[list[Group]] = relationship("Group", back_populates="project", cascade="all, delete-orphan")
    render_preset: Mapped[RenderPreset | None] = relationship("RenderPreset", foreign_keys=[render_preset_id], lazy="joined")
    character: Mapped[object | None] = relationship("Character", foreign_keys=[character_id])
    style_profile: Mapped[StyleProfile | None] = relationship("StyleProfile", foreign_keys=[style_profile_id])
