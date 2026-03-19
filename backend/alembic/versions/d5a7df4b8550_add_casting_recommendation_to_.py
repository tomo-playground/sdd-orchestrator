"""add_casting_recommendation_to_storyboards

Revision ID: d5a7df4b8550
Revises: 136a62ea8e04
Create Date: 2026-02-28 10:35:09.382213

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a7df4b8550"
down_revision: str | Sequence[str] | None = "136a62ea8e04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "storyboards", sa.Column("casting_recommendation", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("storyboards", "casting_recommendation")
