from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project


class MediaAsset(Base, TimestampMixin):
    """Registry of all media files (images, videos, audio) stored in local or cloud storage."""

    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Hierarchy Reference
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id"), nullable=True)
    storyboard_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("storyboards.id"), nullable=True)
    scene_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scenes.id"), nullable=True)

    # File details
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'image', 'video', 'audio', 'cache', 'candidate'
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True) # The key/path in S3 or local
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))

    # Hash for integrity/deduplication
    checksum: Mapped[str | None] = mapped_column(String(64)) # SHA-256

    # Relationships
    project: Mapped[Project | None] = relationship("Project", back_populates="media_assets")
