"""add last_thread_id to storyboards

Revision ID: 1c11eaba13d6
Revises: d4d359f86412
Create Date: 2026-03-28 09:33:18.828395

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c11eaba13d6"
down_revision: str | Sequence[str] | None = "d4d359f86412"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("storyboards", sa.Column("last_thread_id", sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("storyboards", "last_thread_id")
