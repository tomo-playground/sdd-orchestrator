"""add_storyboard_characters

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-02-06

Add storyboard_characters table for speaker-to-character mapping in Dialogue mode.
"""

import sqlalchemy as sa

from alembic import op

revision = "y9z0a1b2c3d4"
down_revision = "502d0f4232de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "storyboard_characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "storyboard_id",
            sa.Integer(),
            sa.ForeignKey("storyboards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("speaker", sa.String(10), nullable=False),
        sa.Column(
            "character_id",
            sa.Integer(),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("storyboard_id", "speaker", name="uq_storyboard_speaker"),
    )
    op.create_index(
        "ix_storyboard_characters_storyboard_id",
        "storyboard_characters",
        ["storyboard_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_storyboard_characters_storyboard_id", table_name="storyboard_characters")
    op.drop_table("storyboard_characters")
