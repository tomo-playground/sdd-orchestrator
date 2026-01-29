from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class TagAlias(Base, TimestampMixin):
    """Tag aliases for replacing risky/invalid tags with safe alternatives.
    
    Examples:
    - "medium shot" → "cowboy_shot"
    - "close up" → "close-up"
    - "unreal engine" → NULL (remove tag)
    """

    __tablename__ = "tag_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_tag: Mapped[str | None] = mapped_column(String(100))  # NULL = remove tag
    reason: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
