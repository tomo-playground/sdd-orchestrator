"""LoRA model for """

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset


class LoRA(Base, TimestampMixin):
    """Simplified LoRA model focusing on core metadata."""

    __tablename__ = "loras"
    __table_args__ = (Index("idx_loras_civitai", "civitai_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))

    # Attributes
    lora_type: Mapped[str | None] = mapped_column(String(20))  # character, style, pose
    base_model: Mapped[str | None] = mapped_column(String(50))  # SD1.5, SDXL, etc.
    gender_locked: Mapped[str | None] = mapped_column(String(10))  # female, male
    trigger_words: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # Configuration (Weights)
    default_weight: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=0.7)
    weight_min: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=0.1)
    weight_max: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=1.0)

    # Calibration & Performance
    optimal_weight: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    calibration_score: Mapped[int | None] = mapped_column(Integer)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # External Metadata & Media
    civitai_id: Mapped[int | None] = mapped_column(Integer)
    civitai_url: Mapped[str | None] = mapped_column(String(500))
    # preview_image_url column removed
    preview_image_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    preview_image_asset: Mapped["MediaAsset"] = relationship(
        foreign_keys=[preview_image_asset_id],
    )

    @property
    def preview_image_url(self) -> str | None:
        if self.preview_image_asset:
            return self.preview_image_asset.url
        return None
