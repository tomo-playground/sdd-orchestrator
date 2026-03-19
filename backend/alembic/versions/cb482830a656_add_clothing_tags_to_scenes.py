"""add_clothing_tags_to_scenes

Revision ID: cb482830a656
Revises: b7c8d9e0f1a2
Create Date: 2026-02-20 18:51:28.507962

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cb482830a656"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add clothing_tags JSONB column to scenes table."""
    op.add_column("scenes", sa.Column("clothing_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove clothing_tags column from scenes table."""
    op.drop_column("scenes", "clothing_tags")
