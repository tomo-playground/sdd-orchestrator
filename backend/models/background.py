from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset
    from models.storyboard import Storyboard
    from models.style_profile import StyleProfile


class Background(Base, TimestampMixin, SoftDeleteMixin):
    """Reusable background reference image for ControlNet Canny."""

    __tablename__ = "backgrounds"
    __table_args__ = (
        Index(
            "ix_backgrounds_storyboard_location_style",
            "storyboard_id",
            "location_key",
            "style_profile_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND storyboard_id IS NOT NULL AND location_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    weight: Mapped[float] = mapped_column(Float, default=0.3)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Phase 18: Stage Workflow — per-storyboard backgrounds
    storyboard_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=True, index=True
    )
    location_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Phase 18-P3: style-aware caching — different style → new background
    style_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    image_asset: Mapped[MediaAsset | None] = relationship("MediaAsset", foreign_keys=[image_asset_id])
    storyboard: Mapped[Storyboard | None] = relationship("Storyboard", foreign_keys=[storyboard_id])
    style_profile: Mapped[StyleProfile | None] = relationship("StyleProfile", foreign_keys=[style_profile_id])

    @property
    def image_url(self) -> str | None:
        if self.image_asset is None:
            return None
        return self.image_asset.url
