"""Add base_model column to loras table.

Revision ID: e2f3a4b5c6d7
Revises: d1a2b3c4e5f6
Create Date: 2026-02-21
"""

import sqlalchemy as sa

from alembic import op

revision = "e2f3a4b5c6d7"
down_revision = "d1a2b3c4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("loras", sa.Column("base_model", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("loras", "base_model")
