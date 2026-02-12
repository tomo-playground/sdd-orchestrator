"""add scene client_id

Revision ID: a8f1b2c3d4e5
Revises: 6aa32b1422f7
Create Date: 2026-02-12

"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a8f1b2c3d4e5"
down_revision = "6aa32b1422f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add column as nullable first
    op.add_column("scenes", sa.Column("client_id", sa.String(36), nullable=True))

    # 2. Backfill existing rows with UUID
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM scenes WHERE client_id IS NULL")).fetchall()
    for row in rows:
        conn.execute(
            sa.text("UPDATE scenes SET client_id = :cid WHERE id = :sid"),
            {"cid": str(uuid4()), "sid": row[0]},
        )

    # 3. Set NOT NULL + unique index
    op.alter_column("scenes", "client_id", nullable=False)
    op.create_index(
        "ix_scenes_client_id",
        "scenes",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_scenes_client_id", table_name="scenes")
    op.drop_column("scenes", "client_id")
