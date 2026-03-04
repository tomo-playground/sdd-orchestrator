"""Lab experiment model for tag render and scene translate experiments."""

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class LabExperiment(Base, TimestampMixin):
    """Single lab experiment record (tag render or scene translate)."""

    __tablename__ = "lab_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str | None] = mapped_column(String(50), index=True)
    experiment_type: Mapped[str] = mapped_column(
        String(20), index=True, default="tag_render"
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # Character reference (nullable for narrator experiments)
    character_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Group reference (required - Lab experiments belong to Groups)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Prompt data
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Prompt Engine metadata (Phase 1 integration)
    final_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    loras_applied: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Experiment inputs
    target_tags: Mapped[list | None] = mapped_column(JSONB)
    sd_params: Mapped[dict | None] = mapped_column(JSONB)

    # Generated image reference
    media_asset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Generation metadata
    seed: Mapped[int | None] = mapped_column(BigInteger)

    # Evaluation results
    match_rate: Mapped[float | None] = mapped_column(Float, index=True)
    wd14_result: Mapped[dict | None] = mapped_column(JSONB)

    # Area B: scene translate
    scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User memo
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
