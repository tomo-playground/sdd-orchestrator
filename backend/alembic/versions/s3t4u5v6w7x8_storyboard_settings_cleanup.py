"""storyboard_settings_cleanup

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-02-04

Storyboard settings cleanup (7-2 #1.7):
- Migrate character_id, style_profile_id, narrator_voice_preset_id from storyboards → group_config
- DROP those columns from storyboards
"""

import sqlalchemy as sa

from alembic import op

revision = "s3t4u5v6w7x8"
down_revision = "r2s3t4u5v6w7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Backfill group_config from storyboard values (first storyboard wins per group)
    # Only fill if group_config field is currently NULL
    op.execute("""
        UPDATE group_config gc
        SET character_id = sub.character_id
        FROM (
            SELECT DISTINCT ON (group_id) group_id, character_id
            FROM storyboards
            WHERE character_id IS NOT NULL AND deleted_at IS NULL
            ORDER BY group_id, updated_at DESC
        ) sub
        WHERE gc.group_id = sub.group_id
          AND gc.character_id IS NULL
    """)

    op.execute("""
        UPDATE group_config gc
        SET style_profile_id = sub.style_profile_id
        FROM (
            SELECT DISTINCT ON (group_id) group_id, style_profile_id
            FROM storyboards
            WHERE style_profile_id IS NOT NULL AND deleted_at IS NULL
            ORDER BY group_id, updated_at DESC
        ) sub
        WHERE gc.group_id = sub.group_id
          AND gc.style_profile_id IS NULL
    """)

    op.execute("""
        UPDATE group_config gc
        SET narrator_voice_preset_id = sub.narrator_voice_preset_id
        FROM (
            SELECT DISTINCT ON (group_id) group_id, narrator_voice_preset_id
            FROM storyboards
            WHERE narrator_voice_preset_id IS NOT NULL AND deleted_at IS NULL
            ORDER BY group_id, updated_at DESC
        ) sub
        WHERE gc.group_id = sub.group_id
          AND gc.narrator_voice_preset_id IS NULL
    """)

    # 2. DROP columns from storyboards
    op.drop_column("storyboards", "character_id")
    op.drop_column("storyboards", "style_profile_id")
    op.drop_constraint("fk_storyboards_narrator_voice_preset_id", "storyboards", type_="foreignkey")
    op.drop_column("storyboards", "narrator_voice_preset_id")


def downgrade() -> None:
    # Re-add columns
    op.add_column("storyboards", sa.Column("character_id", sa.Integer(), nullable=True))
    op.add_column("storyboards", sa.Column("style_profile_id", sa.Integer(), nullable=True))
    op.add_column(
        "storyboards",
        sa.Column(
            "narrator_voice_preset_id",
            sa.Integer(),
            sa.ForeignKey("voice_presets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Best-effort: copy group_config values back to all storyboards in that group
    op.execute("""
        UPDATE storyboards sb
        SET character_id = gc.character_id,
            style_profile_id = gc.style_profile_id,
            narrator_voice_preset_id = gc.narrator_voice_preset_id
        FROM group_config gc
        WHERE gc.group_id = sb.group_id
    """)
