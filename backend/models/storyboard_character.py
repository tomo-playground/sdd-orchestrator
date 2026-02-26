"""StoryboardCharacter model for mapping speakers to characters in dialogue storyboards."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.character import Character
    from models.storyboard import Storyboard


class StoryboardCharacter(Base):
    """Maps a speaker label (A, B) to a Character for a given Storyboard."""

    __tablename__ = "storyboard_characters"
    __table_args__ = (UniqueConstraint("storyboard_id", "speaker", name="uq_storyboard_speaker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storyboard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("storyboards.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker: Mapped[str] = mapped_column(String(10), nullable=False)
    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    storyboard: Mapped[Storyboard] = relationship("Storyboard", back_populates="characters")
    character: Mapped[Character] = relationship("Character")
