"""add bgm pipeline columns to storyboards

Revision ID: b7c8d9e0f1a2
Revises: 16f123a1b8b8
Create Date: 2026-02-20

Phase 12-C: AI BGM Pipeline — bgm_prompt, bgm_mood, bgm_audio_asset_id
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "16f123a1b8b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("storyboards", sa.Column("bgm_prompt", sa.Text(), nullable=True))
    op.add_column("storyboards", sa.Column("bgm_mood", sa.String(50), nullable=True))
    op.add_column(
        "storyboards",
        sa.Column("bgm_audio_asset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_storyboards_bgm_audio_asset",
        "storyboards",
        "media_assets",
        ["bgm_audio_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_storyboards_bgm_audio_asset", "storyboards", type_="foreignkey")
    op.drop_column("storyboards", "bgm_audio_asset_id")
    op.drop_column("storyboards", "bgm_mood")
    op.drop_column("storyboards", "bgm_prompt")
