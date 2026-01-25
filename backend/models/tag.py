"""Tag, TagRule, Synonym, and TagEffectiveness models."""

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
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

    # Dynamic classification fields (15.7)
    classification_source: Mapped[str | None] = mapped_column(
        String(20), default="pattern"
    )  # 'pattern', 'danbooru', 'llm', 'manual'
    classification_confidence: Mapped[float | None] = mapped_column(Float, default=1.0)

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


class ClassificationRule(Base):
    """Pattern-based tag classification rules (replaces hardcoded CATEGORY_PATTERNS)."""

    __tablename__ = "classification_rules"
    __table_args__ = (
        UniqueConstraint("rule_type", "pattern"),
        Index("idx_classification_rules_active", "active"),
        Index("idx_classification_rules_group", "target_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'suffix', 'prefix', 'contains', 'exact'
    pattern: Mapped[str] = mapped_column(String(100), nullable=False)
    target_group: Mapped[str] = mapped_column(String(50), nullable=False)  # hair_color, expression, etc.
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher = checked first
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Synonym(Base):
    """Synonym mapping for tags."""

    __tablename__ = "synonyms"
    __table_args__ = (UniqueConstraint("tag_id", "synonym"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"))
    synonym: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    tag: Mapped["Tag"] = relationship("Tag", back_populates="synonyms")


class TagEffectiveness(Base, TimestampMixin):
    """Track tag effectiveness based on WD14 feedback loop.

    Measures how well each tag is expressed by the SD model:
    - use_count: Number of times this tag was used in prompts
    - match_count: Number of times WD14 detected this tag in generated images
    - total_confidence: Sum of WD14 confidence scores when detected
    - effectiveness: match_count / use_count (0.0 ~ 1.0)

    High effectiveness (>0.7) = SD model reliably produces this tag
    Low effectiveness (<0.3) = SD model struggles with this tag
    """

    __tablename__ = "tag_effectiveness"
    __table_args__ = (
        Index("idx_tag_effectiveness_score", "effectiveness"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    effectiveness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    tag: Mapped["Tag"] = relationship("Tag", backref="effectiveness_stats")
