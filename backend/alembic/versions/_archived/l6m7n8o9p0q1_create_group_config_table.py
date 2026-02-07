"""Create group_config table and migrate data from groups.

Separates configuration from content table (groups -> group_config).
Non-destructive: keeps existing columns on groups for rollback safety.

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-02-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision: str = "l6m7n8o9p0q1"
down_revision: str | Sequence[str] | None = "k5l6m7n8o9p0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_table()
    _migrate_data_forward()


def downgrade() -> None:
    _migrate_data_back()
    op.drop_table("group_config")


def _create_table() -> None:
    """Create the group_config table with all FK constraints and indexes."""
    op.create_table(
        "group_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "render_preset_id",
            sa.Integer(),
            sa.ForeignKey("render_presets.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "default_character_id",
            sa.Integer(),
            sa.ForeignKey("characters.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "default_style_profile_id",
            sa.Integer(),
            sa.ForeignKey("style_profiles.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "narrator_voice_preset_id",
            sa.Integer(),
            sa.ForeignKey("voice_presets.id", ondelete="SET NULL"),
        ),
        sa.Column("language", sa.String(20)),
        sa.Column("structure", sa.String(30)),
        sa.Column("duration", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    # FK indexes for join performance
    op.create_index("ix_group_config_group_id", "group_config", ["group_id"])
    op.create_index("ix_group_config_render_preset_id", "group_config", ["render_preset_id"])
    op.create_index("ix_group_config_default_character_id", "group_config", ["default_character_id"])
    op.create_index("ix_group_config_default_style_profile_id", "group_config", ["default_style_profile_id"])
    op.create_index("ix_group_config_narrator_voice_preset_id", "group_config", ["narrator_voice_preset_id"])


def _migrate_data_forward() -> None:
    """Copy existing config from groups columns into group_config rows.

    Also picks narrator_voice_preset_id from the latest storyboard per group.
    """
    conn = op.get_bind()

    # Step 1: Create group_config rows from existing groups columns
    conn.execute(
        text("""
            INSERT INTO group_config (
                group_id, render_preset_id,
                default_character_id, default_style_profile_id
            )
            SELECT
                id, render_preset_id,
                default_character_id, default_style_profile_id
            FROM groups
        """)
    )

    # Step 2: Copy narrator_voice_preset_id from latest storyboard per group
    conn.execute(
        text("""
            UPDATE group_config gc
            SET narrator_voice_preset_id = sub.narrator_voice_preset_id
            FROM (
                SELECT DISTINCT ON (group_id)
                    group_id, narrator_voice_preset_id
                FROM storyboards
                WHERE narrator_voice_preset_id IS NOT NULL
                ORDER BY group_id, created_at DESC
            ) sub
            WHERE gc.group_id = sub.group_id
        """)
    )


def _migrate_data_back() -> None:
    """Copy group_config data back to groups columns before dropping table."""
    conn = op.get_bind()
    conn.execute(
        text("""
            UPDATE groups g
            SET
                render_preset_id = gc.render_preset_id,
                default_character_id = gc.default_character_id,
                default_style_profile_id = gc.default_style_profile_id
            FROM group_config gc
            WHERE g.id = gc.group_id
        """)
    )
