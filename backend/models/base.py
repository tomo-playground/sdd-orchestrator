"""SQLAlchemy Base and common utilities."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class SoftDeleteMixin:
    """Mixin for soft delete support via deleted_at timestamp."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None, index=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
