"""Add controlnet_pose to scenes

Revision ID: p3i4j5k6l7m8
Revises: o2h3i4j5k6l7
Create Date: 2026-02-22 20:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "p3i4j5k6l7m8"
down_revision = "o2h3i4j5k6l7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("controlnet_pose", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("scenes", "controlnet_pose")
