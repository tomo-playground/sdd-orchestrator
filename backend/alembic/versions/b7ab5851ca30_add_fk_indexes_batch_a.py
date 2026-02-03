"""Phase 6-5 Batch A: DB Integrity (FK + indexes + orphan cleanup)

P0: 6x *_asset_id FK (SET NULL), scenes.storyboard_id CASCADE, media_assets composite index
P1: scene_character_actions indexes + UNIQUE, tag_rules FK (CASCADE)
Cleanup: orphan media_assets (character owner), orphan scene_quality_scores

Revision ID: b7ab5851ca30
Revises: 1f60e2603354
Create Date: 2026-02-01 15:16:28.593248

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7ab5851ca30"
down_revision: str | Sequence[str] | None = "1f60e2603354"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add FK constraints, indexes, and clean up orphan records."""

    # ------------------------------------------------------------------
    # 0. Orphan data cleanup (BEFORE adding constraints)
    # ------------------------------------------------------------------

    # 0a. Delete orphan media_assets where owner_type='character' and owner doesn't exist
    op.execute(
        """
        DELETE FROM media_assets
        WHERE owner_type = 'character'
          AND owner_id NOT IN (SELECT id FROM characters)
        """
    )

    # 0b. Delete all scene_quality_scores (787 rows, all orphans)
    op.execute("DELETE FROM scene_quality_scores")

    # ------------------------------------------------------------------
    # P0-1. Add FK: 6 tables *_asset_id -> media_assets.id (SET NULL)
    # ------------------------------------------------------------------

    op.create_foreign_key(
        "fk_characters_preview_image_asset_id",
        "characters", "media_assets",
        ["preview_image_asset_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_scenes_image_asset_id",
        "scenes", "media_assets",
        ["image_asset_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_storyboards_video_asset_id",
        "storyboards", "media_assets",
        ["video_asset_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_loras_preview_image_asset_id",
        "loras", "media_assets",
        ["preview_image_asset_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_sd_models_preview_image_asset_id",
        "sd_models", "media_assets",
        ["preview_image_asset_id"], ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_projects_avatar_asset_id",
        "projects", "media_assets",
        ["avatar_asset_id"], ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # P0-2. Change scenes.storyboard_id FK to CASCADE
    # ------------------------------------------------------------------

    op.drop_constraint("scenes_storyboard_id_fkey", "scenes", type_="foreignkey")
    op.create_foreign_key(
        "fk_scenes_storyboard_id",
        "scenes", "storyboards",
        ["storyboard_id"], ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------
    # P0-3. media_assets: composite index (owner_type, owner_id)
    #        replacing two single-column indexes
    # ------------------------------------------------------------------

    op.drop_index("ix_media_assets_owner_id", table_name="media_assets")
    op.drop_index("ix_media_assets_owner_type", table_name="media_assets")
    op.create_index(
        "ix_media_assets_owner", "media_assets",
        ["owner_type", "owner_id"],
    )

    # ------------------------------------------------------------------
    # P1-4. scene_character_actions: indexes + UNIQUE constraint
    # ------------------------------------------------------------------

    op.create_index("ix_sca_scene_id", "scene_character_actions", ["scene_id"])
    op.create_index("ix_sca_character_id", "scene_character_actions", ["character_id"])
    op.create_unique_constraint(
        "uq_sca_scene_character_tag",
        "scene_character_actions",
        ["scene_id", "character_id", "tag_id"],
    )

    # ------------------------------------------------------------------
    # P1-5. tag_rules: FK to tags.id (CASCADE)
    # ------------------------------------------------------------------

    op.create_foreign_key(
        "fk_tag_rules_source_tag_id",
        "tag_rules", "tags",
        ["source_tag_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_tag_rules_target_tag_id",
        "tag_rules", "tags",
        ["target_tag_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Reverse all changes (data cleanup is not reversible)."""

    # P1-5. Drop tag_rules FK
    op.drop_constraint("fk_tag_rules_target_tag_id", "tag_rules", type_="foreignkey")
    op.drop_constraint("fk_tag_rules_source_tag_id", "tag_rules", type_="foreignkey")

    # P1-4. Drop scene_character_actions indexes + UNIQUE
    op.drop_constraint("uq_sca_scene_character_tag", "scene_character_actions", type_="unique")
    op.drop_index("ix_sca_scene_id", table_name="scene_character_actions")
    op.drop_index("ix_sca_character_id", table_name="scene_character_actions")

    # P0-3. Restore single-column indexes on media_assets
    op.drop_index("ix_media_assets_owner", table_name="media_assets")
    op.create_index("ix_media_assets_owner_type", "media_assets", ["owner_type"])
    op.create_index("ix_media_assets_owner_id", "media_assets", ["owner_id"])

    # P0-2. Restore scenes.storyboard_id FK without CASCADE
    op.drop_constraint("fk_scenes_storyboard_id", "scenes", type_="foreignkey")
    op.create_foreign_key(
        "scenes_storyboard_id_fkey",
        "scenes", "storyboards",
        ["storyboard_id"], ["id"],
    )

    # P0-1. Drop all *_asset_id FK constraints
    op.drop_constraint("fk_projects_avatar_asset_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_sd_models_preview_image_asset_id", "sd_models", type_="foreignkey")
    op.drop_constraint("fk_loras_preview_image_asset_id", "loras", type_="foreignkey")
    op.drop_constraint("fk_storyboards_video_asset_id", "storyboards", type_="foreignkey")
    op.drop_constraint("fk_scenes_image_asset_id", "scenes", type_="foreignkey")
    op.drop_constraint("fk_characters_preview_image_asset_id", "characters", type_="foreignkey")

    # Note: Orphan data deletion (step 0) cannot be reversed.
