"""Tag, TagRule, and Synonym models."""

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """Tag model for SD prompt tags."""

    __tablename__ = "tags"
    __table_args__ = (
        Index("idx_tags_category", "category"),
        Index("idx_tags_group", "group_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # character, scene, meta
    group_name: Mapped[str | None] = mapped_column(String(50))  # hair_color, eye_color, etc.
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=True)  # 1=highest, 99=lowest
    exclusive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # single select in group

    # Relationships
    synonyms: Mapped[list["Synonym"]] = relationship("Synonym", back_populates="tag", cascade="all, delete-orphan")


class TagRule(Base):
    """Tag conflict and dependency rules."""

    __tablename__ = "tag_rules"
    __table_args__ = (UniqueConstraint("rule_type", "source_tag_id", "target_tag_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'conflict' or 'requires'
    source_tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"))
    target_tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"))


class Synonym(Base):
    """Synonym mapping for tags."""

    __tablename__ = "synonyms"
    __table_args__ = (UniqueConstraint("tag_id", "synonym"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"))
    synonym: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    tag: Mapped["Tag"] = relationship("Tag", back_populates="synonyms")
