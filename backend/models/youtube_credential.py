"""YouTubeCredential model — one YouTube channel per project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project


class YouTubeCredential(Base, TimestampMixin):
    """One-to-one YouTube OAuth credential per project."""

    __tablename__ = "youtube_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    channel_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    channel_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
