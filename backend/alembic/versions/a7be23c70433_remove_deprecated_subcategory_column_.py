"""Remove deprecated subcategory column from tags table

Revision ID: a7be23c70433
Revises: e839f66f1899
Create Date: 2026-01-30 13:00:09.019469

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7be23c70433'
down_revision: str | Sequence[str] | None = 'e839f66f1899'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove deprecated subcategory column from tags table.

    The subcategory field was deprecated in Phase 6-4.25 (2026-01-30).
    All values were set to NULL and code removed subcategory priority logic.
    Now physically removing the column to clean up schema.
    """
    # Drop index first if it exists
    op.drop_index('ix_tags_subcategory', table_name='tags', if_exists=True)

    # Remove the column
    op.drop_column('tags', 'subcategory')


def downgrade() -> None:
    """Restore subcategory column (as deprecated/unused)."""
    # Re-add column (but leave all values NULL since data was cleared)
    op.add_column('tags', sa.Column('subcategory', sa.String(50), nullable=True))

    # Re-create index
    op.create_index('ix_tags_subcategory', 'tags', ['subcategory'])
