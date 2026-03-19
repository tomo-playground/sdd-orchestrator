"""drop characters.reference_images column

Revision ID: 06678a84288b
Revises: a1c2d3e4f5g6
Create Date: 2026-03-02 00:34:34.856230

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "06678a84288b"
down_revision: str | Sequence[str] | None = "a1c2d3e4f5g6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop reference_images — never actually used; preview_image_asset_id serves as reference."""
    op.drop_column("characters", "reference_images")


def downgrade() -> None:
    op.add_column("characters", sa.Column("reference_images", JSONB(), nullable=True))
