"""Remove structure from group_config.

Revision ID: e1b2c3d4f5g6
Revises: d5a7df4b8550
Create Date: 2026-02-28

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e1b2c3d4f5g6"
down_revision = "d5a7df4b8550"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("group_config", "structure")


def downgrade() -> None:
    op.add_column(
        "group_config",
        sa.Column("structure", sa.String(30), nullable=True),
    )
