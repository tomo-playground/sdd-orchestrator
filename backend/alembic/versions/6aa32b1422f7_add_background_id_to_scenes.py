"""add background_id to scenes

Revision ID: 6aa32b1422f7
Revises: 31d2ba4ec309
Create Date: 2026-02-12

"""

import sqlalchemy as sa

from alembic import op

revision = "6aa32b1422f7"
down_revision = "31d2ba4ec309"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenes",
        sa.Column(
            "background_id",
            sa.Integer(),
            sa.ForeignKey("backgrounds.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_scenes_background_id", "scenes", ["background_id"])


def downgrade() -> None:
    op.drop_index("ix_scenes_background_id", table_name="scenes")
    op.drop_column("scenes", "background_id")
