"""drop_storyboard_video_columns

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-02-04

Drop video_asset_id and recent_videos from storyboards (now in render_history).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "u5v6w7x8y9z0"
down_revision = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_storyboards_video_asset_id", "storyboards", type_="foreignkey")
    op.drop_column("storyboards", "video_asset_id")
    op.drop_column("storyboards", "recent_videos")


def downgrade() -> None:
    op.add_column(
        "storyboards",
        sa.Column("recent_videos", JSONB, nullable=True),
    )
    op.add_column(
        "storyboards",
        sa.Column("video_asset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_storyboards_video_asset_id",
        "storyboards",
        "media_assets",
        ["video_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
