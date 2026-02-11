from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset


class Background(Base, TimestampMixin, SoftDeleteMixin):
    """Reusable background reference image for ControlNet Canny."""

    __tablename__ = "backgrounds"

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

    # Relationships
    image_asset: Mapped[MediaAsset | None] = relationship("MediaAsset", foreign_keys=[image_asset_id])

    @property
    def image_url(self) -> str | None:
        if self.image_asset is None:
            return None
        return self.image_asset.url
