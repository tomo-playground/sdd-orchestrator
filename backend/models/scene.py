"""Scene and Storyboard models."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.associations import SceneCharacterAction, SceneTag
    from models.storyboard import Storyboard


class Scene(Base, TimestampMixin):
    """A single scene/shot in a storyboard."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storyboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("storyboards.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    script: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)  # LLM generated visual description

    # Scene metadata
    speaker: Mapped[str | None] = mapped_column(String(20), default="Narrator")
    duration: Mapped[float | None] = mapped_column(Float, default=3.0)

    # Prompt fields
    image_prompt: Mapped[str | None] = mapped_column(Text)
    image_prompt_ko: Mapped[str | None] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)

    # Image Generation Params (Optional overrides)
    width: Mapped[int] = mapped_column(Integer, default=512)
    height: Mapped[int] = mapped_column(Integer, default=768)
    steps: Mapped[int | None] = mapped_column(Integer)
    cfg_scale: Mapped[float | None] = mapped_column(Float)
    sampler_name: Mapped[str | None] = mapped_column(String(50))
    seed: Mapped[int | None] = mapped_column(BigInteger)
    clip_skip: Mapped[int | None] = mapped_column(Integer)

    # Context tags (JSONB for flexible tag groups)
    context_tags: Mapped[dict | None] = mapped_column(JSONB)

    # Generated Image Path
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    storyboard: Mapped["Storyboard"] = relationship("Storyboard", back_populates="scenes")

    # Global/Ambient tags (Weather, Location, etc.)
    tags: Mapped[list["SceneTag"]] = relationship("SceneTag", backref="scene", cascade="all, delete-orphan")

    # Character actions in this scene
    character_actions: Mapped[list["SceneCharacterAction"]] = relationship(
        "SceneCharacterAction", backref="scene", cascade="all, delete-orphan"
    )
