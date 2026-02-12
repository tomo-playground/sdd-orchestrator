"""add storyboard version for optimistic locking

Revision ID: b5e6f7a8c9d0
Revises: a8f1b2c3d4e5
Create Date: 2026-02-12

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b5e6f7a8c9d0"
down_revision = "a8f1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "storyboards",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("storyboards", "version")
