"""Drop voice_preset_id from render_presets, character_id from group_config.

These fields are redundant:
- RenderPreset.voice_preset_id: replaced by GroupConfig.narrator_voice_preset_id
- GroupConfig.character_id: characters are set at storyboard level via storyboard_characters

Revision ID: z0a1b2c3d4e5
Revises: 47a01a32f858
Create Date: 2026-02-06
"""

import sqlalchemy as sa

from alembic import op

revision = "z0a1b2c3d4e5"
down_revision = "47a01a32f858"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop character_id from group_config (no index exists, just FK)
    op.drop_constraint("group_config_character_id_fkey", "group_config", type_="foreignkey")
    op.drop_column("group_config", "character_id")

    # 2. Drop voice_preset_id from render_presets
    op.drop_index("ix_render_presets_voice_preset_id", table_name="render_presets")
    op.drop_column("render_presets", "voice_preset_id")


def downgrade() -> None:
    # Restore voice_preset_id to render_presets
    op.add_column(
        "render_presets",
        sa.Column("voice_preset_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_render_presets_voice_preset_id", "render_presets", ["voice_preset_id"])

    # Restore character_id to group_config (no index needed, just FK)
    op.add_column(
        "group_config",
        sa.Column("character_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "group_config_character_id_fkey",
        "group_config",
        "characters",
        ["character_id"],
        ["id"],
        ondelete="SET NULL",
    )
