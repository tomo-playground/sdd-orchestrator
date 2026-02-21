"""Add style_profile_id to characters table.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-02-21
"""

import sqlalchemy as sa

from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None

# Explicit mapping: character_id -> style_profile_id
EXPLICIT_MAPPING = {
    3: 1,   # Midoriya → Default Anime
    8: 3,   # Flat Color Girl → Flat Color Anime
    9: 1,   # Harukaze Doremi → Default Anime (fallback)
    12: 3,  # Flat Color Boy → Flat Color Anime
    13: 4,  # J_huiben Girl → Children Picture Book
    14: 4,  # J_huiben Boy → Children Picture Book
}


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("style_profile_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_characters_style_profile_id",
        "characters",
        "style_profiles",
        ["style_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_characters_style_profile_id",
        "characters",
        ["style_profile_id"],
    )

    # Data migration: map existing characters to style profiles
    characters = sa.table(
        "characters",
        sa.column("id", sa.Integer),
        sa.column("style_profile_id", sa.Integer),
    )
    for char_id, profile_id in EXPLICIT_MAPPING.items():
        op.execute(
            characters.update()
            .where(characters.c.id == char_id)
            .values(style_profile_id=profile_id)
        )


def downgrade() -> None:
    op.drop_index("ix_characters_style_profile_id", table_name="characters")
    op.drop_constraint("fk_characters_style_profile_id", "characters", type_="foreignkey")
    op.drop_column("characters", "style_profile_id")
