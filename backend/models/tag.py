"""Tag model for Pure V3 Prompt Engine."""

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """Essential Tag model with 12-Layer semantic data."""

    __tablename__ = "tags"
    __table_args__ = (
        Index("idx_tags_layer", "default_layer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ko_name: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(50), index=True)  # indoor, outdoor, time, clothing, etc.
    description: Mapped[str | None] = mapped_column(String(500))
    
    # V3 Logic: The core of the 12-Layer system
    default_layer: Mapped[int] = mapped_column(Integer, default=0)  # 0-11
    usage_scope: Mapped[str] = mapped_column(String(20), default="ANY") # PERMANENT, TRANSIENT, ANY
    
    # Metadata for sorting/recommendation
    wd14_count: Mapped[int] = mapped_column(Integer, default=0)
    wd14_category: Mapped[int] = mapped_column(Integer, default=0)
    # Classification data (15.7)
    group_name: Mapped[str | None] = mapped_column(String(50))
    classification_source: Mapped[str | None] = mapped_column(String(20))
    classification_confidence: Mapped[float | None] = mapped_column(default=0.0)
    priority: Mapped[int] = mapped_column(Integer, default=100)

class ClassificationRule(Base, TimestampMixin):
    """Dynamic tag classification rules (15.7)."""

    __tablename__ = "classification_rules"
    __table_args__ = (
        Index("idx_rules_pattern", "rule_type", "pattern", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20)) # exact, prefix, suffix, contains
    pattern: Mapped[str] = mapped_column(String(100))
    target_group: Mapped[str] = mapped_column(String(50))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(default=True)

class TagRule(Base, TimestampMixin):
    """Rules for tag interactions (conflict, requires)."""

    __tablename__ = "tag_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20)) # conflict, requires
    source_tag_id: Mapped[int] = mapped_column(Integer, index=True)
    target_tag_id: Mapped[int] = mapped_column(Integer, index=True)
    message: Mapped[str | None] = mapped_column(String(200))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(default=True)
