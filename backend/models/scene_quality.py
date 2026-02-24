"""Scene Quality Score model."""

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class SceneQualityScore(Base, TimestampMixin):
    """Tracks WD14 validation results for generated scenes."""

    __tablename__ = "scene_quality_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storyboard_id: Mapped[int | None] = mapped_column(Integer, index=True)
    scene_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenes.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str | None] = mapped_column(Text)

    # Validation Results
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    matched_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    missing_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    extra_tags: Mapped[list[str] | None] = mapped_column(JSONB)

    # Identity Consistency (Phase 16-D)
    identity_score: Mapped[float | None] = mapped_column(Float)
    identity_tags_detected: Mapped[dict | None] = mapped_column(JSONB)

    validated_at: Mapped[DateTime] = mapped_column(DateTime)

    # Relationships
    scene = relationship("Scene", foreign_keys=[scene_id], viewonly=True)

    @property
    def image_url(self) -> str | None:
        """Derive image URL from scene's linked media asset."""
        if self.scene and self.scene.image_asset:
            return self.scene.image_asset.url
        return None
