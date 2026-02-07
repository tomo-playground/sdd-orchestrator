"""render_history_drop_video_url

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-02-05

Remove video_url column, make media_asset_id NOT NULL with CASCADE.
Rows with NULL media_asset_id are deleted (no asset = no value).
"""

import sqlalchemy as sa

from alembic import op

revision = "v6w7x8y9z0a1"
down_revision = "u5v6w7x8y9z0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Delete rows without a media asset (useless without video_url)
    deleted = conn.execute(
        sa.text("DELETE FROM render_history WHERE media_asset_id IS NULL")
    )
    if deleted.rowcount:
        print(f"  Deleted {deleted.rowcount} render_history rows with NULL media_asset_id")

    # 2. Drop video_url column
    op.drop_column("render_history", "video_url")

    # 3. Change FK: SET NULL → CASCADE, nullable → NOT NULL
    op.drop_constraint(
        "render_history_media_asset_id_fkey", "render_history", type_="foreignkey"
    )
    op.alter_column(
        "render_history",
        "media_asset_id",
        nullable=False,
        existing_type=sa.Integer(),
    )
    op.create_foreign_key(
        "render_history_media_asset_id_fkey",
        "render_history",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert FK to SET NULL + nullable
    op.drop_constraint(
        "render_history_media_asset_id_fkey", "render_history", type_="foreignkey"
    )
    op.alter_column(
        "render_history",
        "media_asset_id",
        nullable=True,
        existing_type=sa.Integer(),
    )
    op.create_foreign_key(
        "render_history_media_asset_id_fkey",
        "render_history",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Re-add video_url (non-nullable — fill with placeholder for existing rows)
    op.add_column(
        "render_history",
        sa.Column("video_url", sa.String(500), nullable=True),
    )
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE render_history SET video_url = '' WHERE video_url IS NULL"))
    op.alter_column("render_history", "video_url", nullable=False, existing_type=sa.String(500))
