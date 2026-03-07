"""Character preset model."""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.associations import CharacterTag
    from models.group import Group
    from models.media_asset import MediaAsset

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Character(Base, TimestampMixin, SoftDeleteMixin):
    """Character preset with identity tags, clothing tags, and multiple LoRAs."""

    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("name", name="uq_characters_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10))  # female, male
    description: Mapped[str | None] = mapped_column(String(500))

    # Multiple LoRAs with weights: [{"lora_id": 1, "weight": 1.0}, ...]
    loras: Mapped[list[dict] | None] = mapped_column(JSONB)

    # Prompt Components — Unified (씬+레퍼런스 공통 외형 프롬프트)
    # positive_prompt: DB character_tags에 없는 추가 보정 (씬/레퍼런스 양쪽 동일 적용)
    # negative_prompt: 경쟁 색상, LoRA 아티팩트 억제 (씬/레퍼런스 양쪽 동일 적용)
    # 레퍼런스 배경(white_background 등)은 config.py 상수로 자동 주입됨
    positive_prompt: Mapped[str | None] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="characters")

    # Relational Tags
    tags: Mapped[list["CharacterTag"]] = relationship("CharacterTag", backref="character", cascade="all, delete-orphan")

    # Media & Display — Reference image for IP-Adapter face consistency
    reference_image_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    reference_image_asset: Mapped["MediaAsset"] = relationship(
        foreign_keys=[reference_image_asset_id],
    )

    @property
    def reference_image_url(self) -> str | None:
        if self.reference_image_asset:
            return self.reference_image_asset.url
        return None

    @property
    def reference_key(self) -> str | None:
        if self.reference_image_asset:
            return self.reference_image_asset.storage_key
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
