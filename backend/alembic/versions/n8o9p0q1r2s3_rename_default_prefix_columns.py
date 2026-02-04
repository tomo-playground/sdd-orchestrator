"""Rename default_character_id → character_id, default_style_profile_id → style_profile_id.

Applies to: projects, storyboards (rename only), groups, group_config (rename + drop character_id).
Groups/group_config do not need character_id (characters are set at storyboard level).
Backfills style_profile_id from project → group → group_config before drop.

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-02-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n8o9p0q1r2s3"
down_revision: str = "m7n8o9p0q1r2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Columns to rename (table, old_column, new_column)
RENAMES = [
    ("projects", "default_character_id", "character_id"),
    ("projects", "default_style_profile_id", "style_profile_id"),
    ("groups", "default_style_profile_id", "style_profile_id"),
    ("group_config", "default_style_profile_id", "style_profile_id"),
    ("storyboards", "default_character_id", "character_id"),
    ("storyboards", "default_style_profile_id", "style_profile_id"),
]

# Columns to drop after rename (groups/group_config don't need character_id)
DROP_COLUMNS = [
    ("groups", "default_character_id"),
    ("group_config", "default_character_id"),
]


def upgrade() -> None:
    # 1. Drop character_id from groups and group_config (not needed at group level)
    for table, col in DROP_COLUMNS:
        op.drop_column(table, col)

    # 2. Rename remaining columns
    for table, old_col, new_col in RENAMES:
        op.alter_column(table, old_col, new_column_name=new_col)

    # 3. Backfill style_profile_id: groups from projects
    op.execute("""
        UPDATE groups g
        SET style_profile_id = p.style_profile_id
        FROM projects p
        WHERE g.project_id = p.id
          AND g.style_profile_id IS NULL
          AND p.style_profile_id IS NOT NULL
    """)

    # 4. Backfill style_profile_id: group_config from groups
    op.execute("""
        UPDATE group_config gc
        SET style_profile_id = g.style_profile_id
        FROM groups g
        WHERE gc.group_id = g.id
          AND gc.style_profile_id IS NULL
          AND g.style_profile_id IS NOT NULL
    """)


def downgrade() -> None:
    # Reverse renames
    for table, old_col, new_col in RENAMES:
        op.alter_column(table, new_col, new_column_name=old_col)

    # Re-add dropped columns
    for table, col in DROP_COLUMNS:
        op.add_column(table, sa.Column(col, sa.Integer(), nullable=True))
