"""drop_image_storage_key_from_activity_logs

Phase 4 (Final): Remove deprecated image_storage_key column.
All image references now go through media_asset_id FK.

Revision ID: e1fd14c87f7b
Revises: f6fbfd298a1b
Create Date: 2026-02-06 17:11:33.016312

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1fd14c87f7b'
down_revision: str | Sequence[str] | None = 'f6fbfd298a1b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop deprecated image_storage_key column."""
    op.drop_column('activity_logs', 'image_storage_key')


def downgrade() -> None:
    """Restore image_storage_key column (data will be lost)."""
    op.add_column(
        'activity_logs',
        sa.Column('image_storage_key', sa.String(500), nullable=True)
    )
