from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.group import Group
    from models.storyboard import Storyboard


class StoryCard(Base, TimestampMixin, SoftDeleteMixin):
    """소재 카드 — 시리즈별 대본 소재 풀."""

    __tablename__ = "story_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cluster: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unused", index=True)

    # 소재 본문
    situation: Mapped[str | None] = mapped_column(Text)
    hook_angle: Mapped[str | None] = mapped_column(Text)
    key_moments: Mapped[list | None] = mapped_column(JSONB)
    emotional_arc: Mapped[dict | None] = mapped_column(JSONB)
    empathy_details: Mapped[list | None] = mapped_column(JSONB)
    characters_hint: Mapped[dict | None] = mapped_column(JSONB)

    # 메타
    hook_score: Mapped[float | None] = mapped_column(Float)
    used_in_storyboard_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("storyboards.id", ondelete="SET NULL"),
        index=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="story_cards")
    used_in_storyboard: Mapped[Storyboard | None] = relationship(
        "Storyboard",
        foreign_keys=[used_in_storyboard_id],
    )
