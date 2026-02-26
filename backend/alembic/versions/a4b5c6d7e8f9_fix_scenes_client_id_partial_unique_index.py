"""fix scenes client_id partial unique index

The ix_scenes_client_id index was created as a plain UNIQUE index,
but the ORM model defines it as a partial unique index with
WHERE deleted_at IS NULL. This migration drops the existing index
and recreates it with the correct partial condition.

This is critical for Soft Delete correctness: without the partial
condition, soft-deleted scenes block new scenes from reusing
the same client_id.

Revision ID: a4b5c6d7e8f9
Revises: 359b1dd3a775
Create Date: 2026-02-26
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a4b5c6d7e8f9"
down_revision = "359b1dd3a775"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing plain unique index
    op.drop_index("ix_scenes_client_id", table_name="scenes")

    # Recreate as partial unique index (only active rows)
    op.execute("CREATE UNIQUE INDEX ix_scenes_client_id ON scenes (client_id) WHERE deleted_at IS NULL")


def downgrade() -> None:
    # Drop the partial unique index
    op.drop_index("ix_scenes_client_id", table_name="scenes")

    # Recreate as plain unique index (original state)
    op.create_index(
        "ix_scenes_client_id",
        "scenes",
        ["client_id"],
        unique=True,
    )
