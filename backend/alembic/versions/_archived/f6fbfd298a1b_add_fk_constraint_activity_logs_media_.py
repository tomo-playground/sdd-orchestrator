"""add_fk_constraint_activity_logs_media_asset

Phase 3: Add FK constraint to activity_logs.media_asset_id.
ON DELETE SET NULL ensures activity_logs remain even if media_asset is deleted.

Revision ID: f6fbfd298a1b
Revises: 86e56cbb96b7
Create Date: 2026-02-06 17:07:58.169259

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6fbfd298a1b"
down_revision: str | Sequence[str] | None = "86e56cbb96b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add FK constraint with ON DELETE SET NULL."""
    op.create_foreign_key(
        "fk_activity_logs_media_asset", "activity_logs", "media_assets", ["media_asset_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Remove FK constraint."""
    op.drop_constraint("fk_activity_logs_media_asset", "activity_logs", type_="foreignkey")
