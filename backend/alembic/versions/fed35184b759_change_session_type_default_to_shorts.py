"""Change session_type default from 'free' to 'shorts'.

Revision ID: fed35184b759
Revises: e5b2d6240c61
Create Date: 2026-02-10
"""

from alembic import op

revision = "fed35184b759"
down_revision = "e5b2d6240c61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "creative_sessions",
        "session_type",
        server_default="shorts",
    )


def downgrade() -> None:
    op.alter_column(
        "creative_sessions",
        "session_type",
        server_default="free",
    )
