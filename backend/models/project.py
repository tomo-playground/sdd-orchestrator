from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group


class Project(Base, TimestampMixin):
    """A YouTube Channel project that holds multiple content groups."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Metadata for the channel/project
    handle: Mapped[str | None] = mapped_column(String(100))  # e.g. @MyChannel
    avatar_key: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    groups: Mapped[list[Group]] = relationship(
        "Group", back_populates="project", cascade="all, delete-orphan"
    )
