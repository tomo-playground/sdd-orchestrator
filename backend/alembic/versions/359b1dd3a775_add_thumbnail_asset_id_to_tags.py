"""add_thumbnail_asset_id_to_tags

Revision ID: 359b1dd3a775
Revises: 0a56f0c8f54a
Create Date: 2026-02-24 21:08:09.543744

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "359b1dd3a775"
down_revision: Union[str, Sequence[str], None] = "0a56f0c8f54a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add thumbnail_asset_id FK to tags table (Phase 15-B)."""
    op.add_column("tags", sa.Column("thumbnail_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tags_thumbnail_asset_id",
        "tags",
        "media_assets",
        ["thumbnail_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove thumbnail_asset_id from tags table."""
    op.drop_constraint("fk_tags_thumbnail_asset_id", "tags", type_="foreignkey")
    op.drop_column("tags", "thumbnail_asset_id")
