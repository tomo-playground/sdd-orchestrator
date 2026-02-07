"""Add voice preset FKs to characters and storyboards.

characters.default_voice_preset_id  -> voice_presets.id
storyboards.narrator_voice_preset_id -> voice_presets.id

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa

revision = "j4k5l6m7n8o9"
down_revision = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("default_voice_preset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_characters_default_voice_preset_id",
        "characters",
        "voice_presets",
        ["default_voice_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_characters_default_voice_preset_id",
        "characters",
        ["default_voice_preset_id"],
    )

    op.add_column(
        "storyboards",
        sa.Column("narrator_voice_preset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_storyboards_narrator_voice_preset_id",
        "storyboards",
        "voice_presets",
        ["narrator_voice_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_storyboards_narrator_voice_preset_id",
        "storyboards",
        ["narrator_voice_preset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_storyboards_narrator_voice_preset_id", table_name="storyboards")
    op.drop_constraint("fk_storyboards_narrator_voice_preset_id", "storyboards", type_="foreignkey")
    op.drop_column("storyboards", "narrator_voice_preset_id")

    op.drop_index("ix_characters_default_voice_preset_id", table_name="characters")
    op.drop_constraint("fk_characters_default_voice_preset_id", "characters", type_="foreignkey")
    op.drop_column("characters", "default_voice_preset_id")
