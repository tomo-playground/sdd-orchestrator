"""SD Model and Style Profile models."""

from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.media_asset import MediaAsset


class SDModel(Base, TimestampMixin):
    """Stable Diffusion checkpoint/model."""

    __tablename__ = "sd_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)  # filename
    display_name: Mapped[str | None] = mapped_column(String(200))
    model_type: Mapped[str] = mapped_column(String(50), default="checkpoint")  # checkpoint, vae, etc.
    base_model: Mapped[str | None] = mapped_column(String(50))  # SD1.5, SDXL, etc.
    civitai_id: Mapped[int | None] = mapped_column(Integer)
    civitai_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Embedding(Base, TimestampMixin):
    """Textual Inversion embeddings (negative embeddings, etc.)."""

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    embedding_type: Mapped[str] = mapped_column(String(50), default="negative")  # negative, positive, style
    trigger_word: Mapped[str | None] = mapped_column(String(100))  # Usually same as name
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StyleProfile(Base, TimestampMixin):
    """Style Profile: SD Model + LoRAs + Embeddings bundle."""

    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # SD Model
    sd_model_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sd_models.id"))
    sd_model: Mapped["SDModel"] = relationship("SDModel")

    # LoRAs (array of {lora_id, weight})
    loras: Mapped[list[dict] | None] = mapped_column(JSONB)  # [{lora_id: 1, weight: 0.8}, ...]

    # Embeddings
    negative_embeddings: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))  # embedding IDs
    positive_embeddings: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    # Default prompts
    default_positive: Mapped[str | None] = mapped_column(Text)  # masterpiece, best quality, ...
    default_negative: Mapped[str | None] = mapped_column(Text)

    # Settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
