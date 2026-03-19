"""add duration and language to storyboards

Revision ID: 92320b5d62f9
Revises: fed35184b759
Create Date: 2026-02-10 17:53:53.967111

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "92320b5d62f9"
down_revision: str | Sequence[str] | None = "fed35184b759"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add duration and language columns to storyboards table."""
    op.add_column("storyboards", sa.Column("duration", sa.Integer(), nullable=True))
    op.add_column("storyboards", sa.Column("language", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove duration and language columns from storyboards table."""
    op.drop_column("storyboards", "language")
    op.drop_column("storyboards", "duration")
