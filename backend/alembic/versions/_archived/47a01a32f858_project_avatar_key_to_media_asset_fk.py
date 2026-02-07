"""project_avatar_key_to_media_asset_fk

Revision ID: 47a01a32f858
Revises: bc30616b440b
Create Date: 2026-02-06 11:34:17.915852

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "47a01a32f858"
down_revision: Union[str, Sequence[str], None] = "bc30616b440b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add new column
    op.add_column("projects", sa.Column("avatar_media_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_avatar_media_asset_id",
        "projects",
        "media_assets",
        ["avatar_media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. Migrate existing avatar_key data to avatar_media_asset_id
    # avatar_key contains storage_key like "characters/9/preview/..."
    # Find matching media_asset by storage_key and set the FK
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE projects p
            SET avatar_media_asset_id = ma.id
            FROM media_assets ma
            WHERE p.avatar_key IS NOT NULL
              AND p.avatar_key = ma.storage_key
        """)
    )

    # 3. Drop old column
    op.drop_column("projects", "avatar_key")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Add old column back
    op.add_column("projects", sa.Column("avatar_key", sa.VARCHAR(length=100), nullable=True))

    # 2. Migrate data back
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE projects p
            SET avatar_key = ma.storage_key
            FROM media_assets ma
            WHERE p.avatar_media_asset_id IS NOT NULL
              AND p.avatar_media_asset_id = ma.id
        """)
    )

    # 3. Drop new column and FK
    op.drop_constraint("fk_projects_avatar_media_asset_id", "projects", type_="foreignkey")
    op.drop_column("projects", "avatar_media_asset_id")
