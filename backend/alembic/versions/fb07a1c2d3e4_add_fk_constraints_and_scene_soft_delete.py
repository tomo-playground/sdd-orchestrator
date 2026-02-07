"""Add FK constraints and scene soft delete.

Changes:
1. scenes.environment_reference_id → FK media_assets.id (SET NULL)
2. activity_logs.storyboard_id → FK storyboards.id (SET NULL)
3. activity_logs.scene_id → FK scenes.id (SET NULL)
4. activity_logs.character_id → FK characters.id (SET NULL)
5. tags.replacement_tag_id → FK tags.id (SET NULL)
6. scenes.deleted_at column (SoftDeleteMixin)

Revision ID: fb07a1c2d3e4
Revises: d2e3f4a5b6c7
Create Date: 2026-02-07
"""

import sqlalchemy as sa
from alembic import op

revision = "fb07a1c2d3e4"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. Clean dangling references before adding FK constraints
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE scenes SET environment_reference_id = NULL
        WHERE environment_reference_id IS NOT NULL
        AND environment_reference_id NOT IN (SELECT id FROM media_assets)
    """))
    conn.execute(sa.text("""
        UPDATE activity_logs SET storyboard_id = NULL
        WHERE storyboard_id IS NOT NULL
        AND storyboard_id NOT IN (SELECT id FROM storyboards)
    """))
    conn.execute(sa.text("""
        UPDATE activity_logs SET scene_id = NULL
        WHERE scene_id IS NOT NULL
        AND scene_id NOT IN (SELECT id FROM scenes)
    """))
    conn.execute(sa.text("""
        UPDATE activity_logs SET character_id = NULL
        WHERE character_id IS NOT NULL
        AND character_id NOT IN (SELECT id FROM characters)
    """))
    conn.execute(sa.text("""
        UPDATE tags SET replacement_tag_id = NULL
        WHERE replacement_tag_id IS NOT NULL
        AND replacement_tag_id NOT IN (SELECT id FROM tags)
    """))

    # 1. scenes.environment_reference_id FK
    op.create_foreign_key(
        "fk_scenes_environment_reference_id",
        "scenes",
        "media_assets",
        ["environment_reference_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. activity_logs.storyboard_id FK
    op.create_foreign_key(
        "fk_activity_logs_storyboard_id",
        "activity_logs",
        "storyboards",
        ["storyboard_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. activity_logs.scene_id FK
    op.create_foreign_key(
        "fk_activity_logs_scene_id",
        "activity_logs",
        "scenes",
        ["scene_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. activity_logs.character_id FK
    op.create_foreign_key(
        "fk_activity_logs_character_id",
        "activity_logs",
        "characters",
        ["character_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 5. tags.replacement_tag_id FK
    op.create_foreign_key(
        "fk_tags_replacement_tag_id",
        "tags",
        "tags",
        ["replacement_tag_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 6. scenes.deleted_at column (SoftDeleteMixin)
    op.add_column(
        "scenes",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_scenes_deleted_at", "scenes", ["deleted_at"])


def downgrade() -> None:
    # 6. Remove scenes.deleted_at
    op.drop_index("ix_scenes_deleted_at", table_name="scenes")
    op.drop_column("scenes", "deleted_at")

    # 5. Remove tags.replacement_tag_id FK
    op.drop_constraint("fk_tags_replacement_tag_id", "tags", type_="foreignkey")

    # 4. Remove activity_logs.character_id FK
    op.drop_constraint("fk_activity_logs_character_id", "activity_logs", type_="foreignkey")

    # 3. Remove activity_logs.scene_id FK
    op.drop_constraint("fk_activity_logs_scene_id", "activity_logs", type_="foreignkey")

    # 2. Remove activity_logs.storyboard_id FK
    op.drop_constraint("fk_activity_logs_storyboard_id", "activity_logs", type_="foreignkey")

    # 1. Remove scenes.environment_reference_id FK
    op.drop_constraint("fk_scenes_environment_reference_id", "scenes", type_="foreignkey")
