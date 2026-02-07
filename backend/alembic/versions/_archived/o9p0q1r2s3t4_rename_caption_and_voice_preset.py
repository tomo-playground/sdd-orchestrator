"""Rename default_caption → caption, default_voice_preset_id → voice_preset_id.

Applies to: storyboards.default_caption, characters.default_voice_preset_id.
Also renames FK constraint and index on characters.

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-02-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "o9p0q1r2s3t4"
down_revision: str = "n8o9p0q1r2s3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENAMES = [
    ("storyboards", "default_caption", "caption"),
    ("characters", "default_voice_preset_id", "voice_preset_id"),
]


def upgrade() -> None:
    # 1. Rename columns
    for table, old_col, new_col in RENAMES:
        op.alter_column(table, old_col, new_column_name=new_col)

    # 2. Rename FK constraint on characters
    op.drop_constraint("fk_characters_default_voice_preset_id", "characters", type_="foreignkey")
    op.create_foreign_key(
        "fk_characters_voice_preset_id",
        "characters",
        "voice_presets",
        ["voice_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Rename index on characters
    op.drop_index("ix_characters_default_voice_preset_id", table_name="characters")
    op.create_index("ix_characters_voice_preset_id", "characters", ["voice_preset_id"])


def downgrade() -> None:
    # Reverse index rename
    op.drop_index("ix_characters_voice_preset_id", table_name="characters")
    op.create_index("ix_characters_default_voice_preset_id", "characters", ["default_voice_preset_id"])

    # Reverse FK rename
    op.drop_constraint("fk_characters_voice_preset_id", "characters", type_="foreignkey")
    op.create_foreign_key(
        "fk_characters_default_voice_preset_id",
        "characters",
        "voice_presets",
        ["default_voice_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Reverse column renames
    for table, old_col, new_col in RENAMES:
        op.alter_column(table, new_col, new_column_name=old_col)
