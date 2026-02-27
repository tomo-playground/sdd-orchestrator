"""Character preset model."""

from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.associations import CharacterTag
    from models.media_asset import MediaAsset
    from models.sd_model import StyleProfile

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Character(Base, TimestampMixin, SoftDeleteMixin):
    """Character preset with identity tags, clothing tags, and multiple LoRAs."""

    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("name", name="uq_characters_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    style_profile_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("style_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10))  # female, male
    description: Mapped[str | None] = mapped_column(String(500))

    # Multiple LoRAs with weights: [{"lora_id": 1, "weight": 1.0}, ...]
    loras: Mapped[list[dict] | None] = mapped_column(JSONB)

    # Prompt Components
    recommended_negative: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    custom_base_prompt: Mapped[str | None] = mapped_column(Text)
    custom_negative_prompt: Mapped[str | None] = mapped_column(Text)

    # Reference image generation prompts (for IP-Adapter reference creation)
    reference_base_prompt: Mapped[str | None] = mapped_column(Text)
    reference_negative_prompt: Mapped[str | None] = mapped_column(Text)

    # Relationships
    style_profile: Mapped["StyleProfile | None"] = relationship(
        "StyleProfile",
        foreign_keys=[style_profile_id],
    )

    # V3: Relational Tags
    tags: Mapped[list["CharacterTag"]] = relationship("CharacterTag", backref="character", cascade="all, delete-orphan")

    # Media & Display
    # preview_image_url column removed
    preview_image_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    preview_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    preview_image_asset: Mapped["MediaAsset"] = relationship(
        foreign_keys=[preview_image_asset_id],
    )

    @property
    def preview_image_url(self) -> str | None:
        if self.preview_image_asset:
            return self.preview_image_asset.url
        return None

    @property
    def preview_key(self) -> str | None:
        if self.preview_image_asset:
            return self.preview_image_asset.storage_key
        return None

    # Voice
    voice_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("voice_presets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # System Settings
    ip_adapter_weight: Mapped[float | None] = mapped_column(Float)
    ip_adapter_model: Mapped[str | None] = mapped_column(String(50))  # clip, clip_face, faceid

    # IP-Adapter guidance (Phase 3-A: per-character override, nullable = use config default)
    ip_adapter_guidance_start: Mapped[float | None] = mapped_column(Float)
    ip_adapter_guidance_end: Mapped[float | None] = mapped_column(Float)

    # Reference source type (Phase 1-A: "generated" | "uploaded")
    reference_source_type: Mapped[str | None] = mapped_column(String(20))

    # Multi-angle references (Phase 2-A)
    # [{"angle": "front", "asset_id": 123}, {"angle": "side_left", "asset_id": 124}]
    reference_images: Mapped[list[dict] | None] = mapped_column(JSONB)
