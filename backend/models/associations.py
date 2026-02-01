"""Association tables for Many-to-Many relationships (V3 Schema)."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.tag import Tag

from models.base import Base


class CharacterTag(Base):
    """Link between Character and Tag with metadata."""

    __tablename__ = "character_tags"

    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to Tag
    tag: Mapped["Tag"] = relationship("Tag")


class SceneTag(Base):
    """Link between Scene and Tag (Ambient/Global tags)."""

    __tablename__ = "scene_tags"

    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    weight: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationship to Tag
    tag: Mapped["Tag"] = relationship("Tag")


class SceneCharacterAction(Base):
    """Link between Scene, Character, and Tag (Action/Expression)."""

    __tablename__ = "scene_character_actions"
    __table_args__ = (
        Index("ix_sca_scene_id", "scene_id"),
        Index("ix_sca_character_id", "character_id"),
        UniqueConstraint("scene_id", "character_id", "tag_id", name="uq_sca_scene_character_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"))
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"))

    weight: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationship to Tag
    tag: Mapped["Tag"] = relationship("Tag")
