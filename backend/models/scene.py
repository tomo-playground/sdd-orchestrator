"""Scene and Storyboard models."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.associations import SceneCharacterAction, SceneTag


class Scene(Base, TimestampMixin):
    """A single scene/shot in a storyboard."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storyboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("storyboards.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    script: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text) # LLM generated visual description

    # Image Generation Params (Optional overrides)
    width: Mapped[int] = mapped_column(Integer, default=512)
    height: Mapped[int] = mapped_column(Integer, default=768)

    # Generated Image Path
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    # Global/Ambient tags (Weather, Location, etc.)
    tags: Mapped[list["SceneTag"]] = relationship("SceneTag", backref="scene", cascade="all, delete-orphan")

    # Character actions in this scene
    character_actions: Mapped[list["SceneCharacterAction"]] = relationship(
        "SceneCharacterAction", backref="scene", cascade="all, delete-orphan"
    )
