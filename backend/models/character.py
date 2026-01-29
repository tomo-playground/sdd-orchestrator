"""Character preset model."""

from sqlalchemy import ARRAY, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.associations import CharacterTag

from models.base import Base, TimestampMixin


class Character(Base, TimestampMixin):
    """Character preset with identity tags, clothing tags, and multiple LoRAs."""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))  # LoRA 조합 설명
    gender: Mapped[str | None] = mapped_column(String(10))  # female, male
    
    # V3: Relational Tags (Replacing identity_tags/clothing_tags)
    # identity_tags: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    # clothing_tags: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    
    tags: Mapped[list["CharacterTag"]] = relationship("CharacterTag", backref="character", cascade="all, delete-orphan")

    # Multiple LoRAs with weights: [{"lora_id": 1, "weight": 1.0}, ...]
    loras: Mapped[list[dict] | None] = mapped_column(JSONB)
    # Validated negative prompt for this character/LoRA combination
    recommended_negative: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    # Custom base prompt (raw text) to be appended to the character's prompt
    custom_base_prompt: Mapped[str | None] = mapped_column(Text)
    # Custom negative prompt (raw text)
    custom_negative_prompt: Mapped[str | None] = mapped_column(Text)
    # Reference image generation prompts (for IP-Adapter reference creation)
    reference_base_prompt: Mapped[str | None] = mapped_column(Text)
    reference_negative_prompt: Mapped[str | None] = mapped_column(Text)
    preview_image_url: Mapped[str | None] = mapped_column(String(500))
    # Prompt generation mode: auto (detect based on LoRA), standard (no LoRA), lora (with LoRA)
    prompt_mode: Mapped[str] = mapped_column(String(20), default="auto")
    # IP-Adapter settings
    ip_adapter_weight: Mapped[float | None] = mapped_column(Float)
    ip_adapter_model: Mapped[str | None] = mapped_column(String(50))  # clip, clip_face, faceid
