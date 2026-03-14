"""Scene and Storyboard models."""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, text  # noqa: F401
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config import DEFAULT_SPEAKER
from models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.associations import SceneCharacterAction, SceneTag
    from models.background import Background
    from models.media_asset import MediaAsset
    from models.storyboard import Storyboard


class Scene(Base, TimestampMixin, SoftDeleteMixin):
    """A single scene/shot in a storyboard."""

    __tablename__ = "scenes"
    __table_args__ = (
        Index("ix_scenes_client_id", "client_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False, default=lambda: str(uuid4()))
    storyboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("storyboards.id", ondelete="CASCADE"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    script: Mapped[str | None] = mapped_column(Text)

    # Scene metadata
    speaker: Mapped[str | None] = mapped_column(String(20), default=DEFAULT_SPEAKER)
    duration: Mapped[float | None] = mapped_column(Float, default=3.0)
    scene_mode: Mapped[str] = mapped_column(
        String(10), default="single", server_default="single"
    )  # "single" | "multi" (2인 동시 출연)

    # Prompt fields
    image_prompt: Mapped[str | None] = mapped_column(Text)
    image_prompt_ko: Mapped[str | None] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)

    # TTS & Pacing (Context-Aware TTS Designer output)
    voice_design_prompt: Mapped[str | None] = mapped_column(Text)
    head_padding: Mapped[float | None] = mapped_column(Float, default=0.0)
    tail_padding: Mapped[float | None] = mapped_column(Float, default=0.0)
    # Linked TTS preview asset (reuse preview TTS in final render)
    tts_asset_id: Mapped[int | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)

    # Image Generation Params (Optional overrides)
    width: Mapped[int] = mapped_column(Integer, default=832)
    height: Mapped[int] = mapped_column(Integer, default=1216)

    # Context tags (JSONB for flexible tag groups)
    context_tags: Mapped[dict | None] = mapped_column(JSONB)

    # Per-scene clothing override (JSONB: {"<character_id>": ["tag1", "tag2"]})
    # null = use character default clothing
    clothing_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Consistency Enhancements
    use_reference_only: Mapped[bool] = mapped_column(Boolean, default=True)
    reference_only_weight: Mapped[float] = mapped_column(Float, default=0.5)
    # Background asset reference (auto-inject tags + ControlNet Canny)
    background_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("backgrounds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    background: Mapped["Background | None"] = relationship("Background", foreign_keys=[background_id], viewonly=True)

    environment_reference_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"), index=True
    )
    environment_reference_weight: Mapped[float] = mapped_column(Float, default=0.3)

    # Per-scene generation settings override (nullable = inherit global)
    use_controlnet: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    controlnet_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    controlnet_pose: Mapped[str | None] = mapped_column(String(50), nullable=True)
    use_ip_adapter: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ip_adapter_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_adapter_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    multi_gen_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    environment_asset: Mapped["MediaAsset | None"] = relationship(
        primaryjoin="Scene.environment_reference_id == MediaAsset.id",
        foreign_keys=[environment_reference_id],
        viewonly=True,
    )

    # Generated Image Path
    # Generated Image Path
    # image_url column removed, use property below
    image_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        index=True,
    )
    image_asset: Mapped["MediaAsset | None"] = relationship(
        foreign_keys=[image_asset_id],
    )

    @property
    def image_url(self) -> str | None:
        if self.image_asset:
            return self.image_asset.url
        return None

    # Candidate images (list of dicts with image_url, match_rate, etc.)
    candidates: Mapped[list[dict] | None] = mapped_column(JSONB)

    # Relationships
    storyboard: Mapped["Storyboard"] = relationship("Storyboard", back_populates="scenes")

    # Global/Ambient tags (Weather, Location, etc.)
    tags: Mapped[list["SceneTag"]] = relationship("SceneTag", backref="scene", cascade="all, delete-orphan")

    # Character actions in this scene
    character_actions: Mapped[list["SceneCharacterAction"]] = relationship(
        "SceneCharacterAction", backref="scene", cascade="all, delete-orphan"
    )
