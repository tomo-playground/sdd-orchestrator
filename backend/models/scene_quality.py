"""Scene Quality Score model."""

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class SceneQualityScore(Base, TimestampMixin):
    """Tracks WD14 validation results for generated scenes."""

    __tablename__ = "scene_quality_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storyboard_id: Mapped[int | None] = mapped_column(Integer, index=True)
    scene_id: Mapped[int] = mapped_column(Integer, index=True)
    image_storage_key: Mapped[str] = mapped_column(String(500))
    prompt: Mapped[str | None] = mapped_column(Text)

    # Validation Results
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    matched_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    missing_tags: Mapped[list[str] | None] = mapped_column(JSONB)
    extra_tags: Mapped[list[str] | None] = mapped_column(JSONB)

    validated_at: Mapped[DateTime] = mapped_column(DateTime)

    @property
    def image_url(self) -> str:
        """Generate URL from storage key at runtime (backward compatibility)."""
        from services.storage import get_storage
        return get_storage().get_url(self.image_storage_key)
