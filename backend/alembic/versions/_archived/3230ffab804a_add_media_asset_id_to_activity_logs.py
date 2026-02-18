"""add_media_asset_id_to_activity_logs

Phase 1: Add media_asset_id column to activity_logs table.
This replaces the direct image_storage_key with a proper FK reference.

Revision ID: 3230ffab804a
Revises: 209d7efeec5f
Create Date: 2026-02-06 17:07:14.614169

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3230ffab804a'
down_revision: str | Sequence[str] | None = '209d7efeec5f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add media_asset_id column and index to activity_logs."""
    # 1. Add nullable column (no FK yet - will add after data migration)
    op.add_column(
        'activity_logs',
        sa.Column('media_asset_id', sa.Integer(), nullable=True)
    )

    # 2. Add index for performance
    op.create_index(
        'ix_activity_logs_media_asset_id',
        'activity_logs',
        ['media_asset_id']
    )


def downgrade() -> None:
    """Remove media_asset_id column and index."""
    op.drop_index('ix_activity_logs_media_asset_id', table_name='activity_logs')
    op.drop_column('activity_logs', 'media_asset_id')
