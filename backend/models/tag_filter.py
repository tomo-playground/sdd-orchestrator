"""Tag filter model for managing ignore/skip tags."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class TagFilter(Base, TimestampMixin):
    """Filter rules for tags (ignore/skip)."""

    __tablename__ = "tag_filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    filter_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'ignore' or 'skip'
    reason: Mapped[str | None] = mapped_column(String(200))  # Why this tag is filtered
    active: Mapped[bool] = mapped_column(Boolean, default=True)
