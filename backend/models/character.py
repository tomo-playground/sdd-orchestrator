"""Character preset model."""

from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.associations import CharacterTag
    from models.media_asset import MediaAsset
    from models.project import Project

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Character(Base, TimestampMixin, SoftDeleteMixin):
    """Character preset with identity tags, clothing tags, and multiple LoRAs."""

    __tablename__ = "characters"
    __table_args__ = (
        UniqueConstraint("name", name="uq_characters_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
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
    project: Mapped["Project | None"] = relationship("Project", foreign_keys=[project_id])

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

    # Voice
    default_voice_preset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("voice_presets.id", ondelete="SET NULL"), nullable=True,
    )

    # System Settings
    prompt_mode: Mapped[str] = mapped_column(String(20), default="auto")  # auto, standard, lora
    ip_adapter_weight: Mapped[float | None] = mapped_column(Float)
    ip_adapter_model: Mapped[str | None] = mapped_column(String(50))  # clip, clip_face, faceid
