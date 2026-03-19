"""Remove unused favorite fields from activity_logs

Revision ID: 4bd92b46246d
Revises: 25105b76ac38
Create Date: 2026-01-30 13:22:18.520737

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4bd92b46246d"
down_revision: str | Sequence[str] | None = "25105b76ac38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove unused favorite/bookmark fields from activity_logs.

    Removed fields (0 usage, 0/184 data):
    - is_favorite: Favorite/bookmark flag (never implemented)
    - name: Human-readable name for favorites (never implemented)

    Favorite functionality was planned but never implemented in UI/API.
    """
    # Drop index first if it exists
    op.drop_index("ix_activity_logs_is_favorite", table_name="activity_logs", if_exists=True)

    # Remove unused columns
    op.drop_column("activity_logs", "is_favorite")
    op.drop_column("activity_logs", "name")


def downgrade() -> None:
    """Restore favorite fields (as unused/empty)."""
    # Re-add columns
    op.add_column("activity_logs", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("activity_logs", sa.Column("name", sa.String(200), nullable=True))

    # Re-create index
    op.create_index("ix_activity_logs_is_favorite", "activity_logs", ["is_favorite"])
