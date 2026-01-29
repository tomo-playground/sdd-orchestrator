"""LoRA model for Pure V3."""

from decimal import Decimal
from sqlalchemy import ARRAY, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class LoRA(Base, TimestampMixin):
    """Simplified LoRA model focusing on core metadata."""

    __tablename__ = "loras"
    __table_args__ = (Index("idx_loras_civitai", "civitai_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    
    # Core attributes
    lora_type: Mapped[str | None] = mapped_column(String(20))  # character, style, pose
    trigger_words: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    default_weight: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=0.7)
    
    # Calibration & Performance
    optimal_weight: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    calibration_score: Mapped[int | None] = mapped_column(Integer)
    
    # Weight range
    weight_min: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=0.1)
    weight_max: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=1.0)
    
    # Metadata
    gender_locked: Mapped[str | None] = mapped_column(String(10))  # female, male
    civitai_id: Mapped[int | None] = mapped_column(Integer)
    civitai_url: Mapped[str | None] = mapped_column(String(500))
    preview_image_url: Mapped[str | None] = mapped_column(String(500))
