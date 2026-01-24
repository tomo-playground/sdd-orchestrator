"""LoRA model."""

from decimal import Decimal

from sqlalchemy import ARRAY, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class LoRA(Base, TimestampMixin):
    """LoRA model for Stable Diffusion LoRAs."""

    __tablename__ = "loras"
    __table_args__ = (Index("idx_loras_civitai", "civitai_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    gender_locked: Mapped[str | None] = mapped_column(String(10))  # female, male, null(자유)
    civitai_id: Mapped[int | None] = mapped_column(Integer)
    civitai_url: Mapped[str | None] = mapped_column(String(500))
    trigger_words: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    default_weight: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=0.7)  # 0.7 for scene expression
    weight_min: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=0.5)
    weight_max: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=1.5)
    base_models: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    character_defaults: Mapped[dict | None] = mapped_column(JSONB)  # {hair_color: "aqua hair", ...}
    recommended_negative: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    preview_image_url: Mapped[str | None] = mapped_column(String(500))
