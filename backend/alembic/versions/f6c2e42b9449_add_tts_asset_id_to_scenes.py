"""add_tts_asset_id_to_scenes

Revision ID: f6c2e42b9449
Revises: x6y7z8a9b0c1
Create Date: 2026-03-05 18:49:19.834980

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6c2e42b9449"
down_revision: str | Sequence[str] | None = "x6y7z8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("scenes", sa.Column("tts_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_scenes_tts_asset_id", "scenes", "media_assets", ["tts_asset_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_scenes_tts_asset_id", "scenes", type_="foreignkey")
    op.drop_column("scenes", "tts_asset_id")
