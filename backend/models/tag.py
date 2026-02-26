"""Tag model for Pure V3 Prompt Engine."""

import re

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from models.base import Base, TimestampMixin

# ASCII + 언더바/하이픈/괄호만 허용 (Danbooru 표준)
_VALID_TAG_NAME = re.compile(r"^[a-z0-9][a-z0-9_\-().+/&!': ]*$")


class Tag(Base, TimestampMixin):
    """Essential Tag model with 12-Layer semantic data."""

    __tablename__ = "tags"
    __table_args__ = (Index("idx_tags_layer", "default_layer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ko_name: Mapped[str | None] = mapped_column(String(100))

    # Taxonomy
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    # subcategory removed (deprecated Phase 6-4.25, removed Phase 6-4.26)
    group_name: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(500))

    # V3 Logic: The core of the 12-Layer system
    default_layer: Mapped[int] = mapped_column(Integer, default=0)  # 0-11
    usage_scope: Mapped[str] = mapped_column(String(20), default="ANY")  # PERMANENT, TRANSIENT, ANY
    priority: Mapped[int] = mapped_column(Integer, default=100)

    @validates("name")
    def _validate_name(self, _key: str, value: str) -> str:
        """비ASCII 태그 거부 (Danbooru 표준 강제)."""
        if value and not _VALID_TAG_NAME.match(value.lower()):
            raise ValueError(f"Invalid tag name (non-ASCII): '{value}'")
        return value

    @validates("group_name")
    def _validate_group_name(self, _key: str, value: str | None) -> str | None:
        """group_name 변경 시 default_layer 자동 동기화."""
        if value is not None:
            from services.keywords.patterns import GROUP_NAME_TO_LAYER

            layer = GROUP_NAME_TO_LAYER.get(value)
            if layer is not None:
                self.default_layer = layer
        return value

    # Classification data (15.7)
    classification_source: Mapped[str | None] = mapped_column(String(20))
    classification_confidence: Mapped[float | None] = mapped_column(default=0.0)

    # WD14 metadata for recommendation
    wd14_count: Mapped[int] = mapped_column(Integer, default=0)
    wd14_category: Mapped[int] = mapped_column(Integer, default=0)

    # Deprecation & replacement (15.8)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    deprecated_reason: Mapped[str | None] = mapped_column(String(200))
    replacement_tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tags.id", ondelete="SET NULL"))

    # Visual Tag Browser (Phase 15-B)
    thumbnail_asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("media_assets.id", ondelete="SET NULL"))
    _thumbnail_asset = relationship(  # type: ignore[misc]
        "MediaAsset", foreign_keys=[thumbnail_asset_id], lazy="joined"
    )

    @property
    def thumbnail_url(self) -> str | None:
        """Response-only: derived from media_asset relationship."""
        return self._thumbnail_asset.url if self._thumbnail_asset else None


class ClassificationRule(Base, TimestampMixin):
    """Dynamic tag classification rules (15.7)."""

    __tablename__ = "classification_rules"
    __table_args__ = (Index("idx_rules_pattern", "rule_type", "pattern", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20))  # exact, prefix, suffix, contains
    pattern: Mapped[str] = mapped_column(String(100))
    target_group: Mapped[str] = mapped_column(String(50))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class TagRule(Base, TimestampMixin):
    """Rules for tag interactions (conflict, requires).

    Tag-level conflicts only (e.g., crying ↔ happy, looking_down ↔ looking_up).
    Category-level was removed (Phase 6-4.26) - never used, logically unnecessary.
    """

    __tablename__ = "tag_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20))  # conflict, requires

    # Tag-level conflicts (individual tags)
    source_tag_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    target_tag_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )

    # Removed (Phase 6-4.26): source_category, target_category
    # Reason: Never used (0/16 rules), logically unnecessary

    message: Mapped[str | None] = mapped_column(String(200))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class TagEffectiveness(Base, TimestampMixin):
    """Per-tag prompt effectiveness tracking (use_count, match_count, ratio)."""

    __tablename__ = "tag_effectiveness"
    __table_args__ = (UniqueConstraint("tag_id", name="uq_tag_effectiveness_tag_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    effectiveness: Mapped[float] = mapped_column(Float, default=0.0)
