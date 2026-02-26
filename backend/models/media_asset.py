from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class MediaAsset(Base, TimestampMixin):
    """Registry of all media files (images, videos, audio) stored in local or cloud storage."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('image', 'audio', 'video', 'cache', 'candidate')",
            name="ck_media_assets_file_type",
        ),
        Index("ix_media_assets_owner", "owner_type", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Generic Relationship (Polymorphic)
    owner_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Garbage Collection Flag
    is_temp: Mapped[bool] = mapped_column(default=False, index=True)

    # File details
    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'image', 'video', 'audio', 'cache', 'candidate'
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)  # The key/path in S3 or local
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))

    # Hash for integrity/deduplication
    checksum: Mapped[str | None] = mapped_column(String(64))  # SHA-256

    # Relationships - Removed specific back_populates to keep it generic
    # Project relationship removed as it's now handled via owner_type='project'
    # Use helper methods in Service to fetch owners if needed.

    @property
    def url(self) -> str:
        from services.storage import get_storage

        storage = get_storage()
        return storage.get_url(self.storage_key)

    @property
    def local_path(self) -> str:
        """Resolve the local filesystem path for this asset.

        For local storage, returns the direct path.
        For S3 storage, downloads to cache first, then returns the cached path.
        Returns the path as a string for compatibility with os.path and open().
        """
        from services.storage import get_storage

        storage = get_storage()
        return str(storage.get_local_path(self.storage_key))
