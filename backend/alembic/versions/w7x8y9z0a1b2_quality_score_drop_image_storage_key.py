"""quality_score_drop_image_storage_key

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-02-05

Drop image_storage_key from scene_quality_scores (redundant with scene_id FK).
Add FK constraint on scene_id → scenes.id with CASCADE.
"""

import sqlalchemy as sa

from alembic import op

revision = "w7x8y9z0a1b2"
down_revision = "v6w7x8y9z0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Delete orphan rows where scene_id doesn't exist in scenes table
    deleted = conn.execute(sa.text("DELETE FROM scene_quality_scores WHERE scene_id NOT IN (SELECT id FROM scenes)"))
    if deleted.rowcount:
        print(f"  Deleted {deleted.rowcount} orphan scene_quality_scores rows")

    # 2. Drop image_storage_key column
    op.drop_column("scene_quality_scores", "image_storage_key")

    # 3. Add FK constraint on scene_id → scenes.id with CASCADE
    op.create_foreign_key(
        "scene_quality_scores_scene_id_fkey",
        "scene_quality_scores",
        "scenes",
        ["scene_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop FK
    op.drop_constraint(
        "scene_quality_scores_scene_id_fkey",
        "scene_quality_scores",
        type_="foreignkey",
    )

    # Re-add image_storage_key (nullable — backfill not possible)
    op.add_column(
        "scene_quality_scores",
        sa.Column("image_storage_key", sa.String(500), nullable=True),
    )
