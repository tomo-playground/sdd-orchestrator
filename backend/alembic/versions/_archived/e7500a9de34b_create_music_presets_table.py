"""create music_presets table and extend render_presets

Revision ID: e7500a9de34b
Revises: 96ca600defd5
Create Date: 2026-02-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7500a9de34b"
down_revision: str | Sequence[str] | None = "96ca600defd5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create music_presets table and add bgm_mode/music_preset_id to render_presets."""
    op.create_table(
        "music_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column(
            "audio_asset_id",
            sa.Integer(),
            sa.ForeignKey("media_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_system", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.add_column("render_presets", sa.Column("bgm_mode", sa.String(20), nullable=True))
    op.add_column(
        "render_presets",
        sa.Column(
            "music_preset_id",
            sa.Integer(),
            sa.ForeignKey("music_presets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop music_presets table and remove bgm_mode/music_preset_id from render_presets."""
    op.drop_column("render_presets", "music_preset_id")
    op.drop_column("render_presets", "bgm_mode")
    op.drop_table("music_presets")
