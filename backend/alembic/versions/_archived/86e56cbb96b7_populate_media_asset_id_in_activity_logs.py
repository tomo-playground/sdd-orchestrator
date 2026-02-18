"""populate_media_asset_id_in_activity_logs

Phase 2: Populate media_asset_id from existing image_storage_key values.
Matches activity_logs.image_storage_key to media_assets.storage_key.

~95% of records will be matched. Unmatched records (5%) remain NULL
because the image was regenerated with a different timestamp.

Revision ID: 86e56cbb96b7
Revises: 3230ffab804a
Create Date: 2026-02-06 17:07:37.528518

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '86e56cbb96b7'
down_revision: str | Sequence[str] | None = '3230ffab804a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate media_asset_id by matching image_storage_key to media_assets.storage_key."""
    # Direct match: image_storage_key = storage_key
    op.execute("""
        UPDATE activity_logs al
        SET media_asset_id = ma.id
        FROM media_assets ma
        WHERE al.image_storage_key = ma.storage_key
          AND al.image_storage_key IS NOT NULL
          AND al.media_asset_id IS NULL;
    """)


def downgrade() -> None:
    """Clear media_asset_id values."""
    op.execute("""
        UPDATE activity_logs
        SET media_asset_id = NULL
        WHERE media_asset_id IS NOT NULL;
    """)
