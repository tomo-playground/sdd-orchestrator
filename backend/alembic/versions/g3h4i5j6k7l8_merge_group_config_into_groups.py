"""Merge group_config into groups table.

Move FK columns (render_preset_id, style_profile_id, narrator_voice_preset_id)
and channel_dna from group_config into groups. Drop group_config table.
Remove language/duration (Storyboard already has these).

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2026-02-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "g3h4i5j6k7l8"
down_revision = "f2g3h4i5j6k7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add columns to groups
    op.add_column("groups", sa.Column("render_preset_id", sa.Integer(), nullable=True))
    op.add_column("groups", sa.Column("style_profile_id", sa.Integer(), nullable=True))
    op.add_column("groups", sa.Column("narrator_voice_preset_id", sa.Integer(), nullable=True))
    op.add_column("groups", sa.Column("channel_dna", postgresql.JSONB(), nullable=True))

    # 2. Migrate data from group_config → groups
    op.execute("""
        UPDATE groups
        SET render_preset_id = gc.render_preset_id,
            style_profile_id = gc.style_profile_id,
            narrator_voice_preset_id = gc.narrator_voice_preset_id,
            channel_dna = gc.channel_dna
        FROM group_config gc
        WHERE groups.id = gc.group_id
    """)

    # 3. Create FK constraints
    op.create_foreign_key(
        "fk_groups_render_preset_id",
        "groups", "render_presets",
        ["render_preset_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_groups_style_profile_id",
        "groups", "style_profiles",
        ["style_profile_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_groups_narrator_voice_preset_id",
        "groups", "voice_presets",
        ["narrator_voice_preset_id"], ["id"],
        ondelete="SET NULL",
    )

    # 4. Drop group_config table
    op.drop_table("group_config")


def downgrade() -> None:
    # 1. Recreate group_config table
    op.create_table(
        "group_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("render_preset_id", sa.Integer(), sa.ForeignKey("render_presets.id", ondelete="SET NULL")),
        sa.Column("style_profile_id", sa.Integer(), sa.ForeignKey("style_profiles.id", ondelete="SET NULL")),
        sa.Column("narrator_voice_preset_id", sa.Integer(), sa.ForeignKey("voice_presets.id", ondelete="SET NULL")),
        sa.Column("language", sa.String(20)),
        sa.Column("duration", sa.Integer()),
        sa.Column("channel_dna", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # 2. Migrate data back from groups → group_config
    op.execute("""
        INSERT INTO group_config (group_id, render_preset_id, style_profile_id, narrator_voice_preset_id, channel_dna)
        SELECT id, render_preset_id, style_profile_id, narrator_voice_preset_id, channel_dna
        FROM groups
    """)

    # 3. Drop FK constraints and columns from groups
    op.drop_constraint("fk_groups_narrator_voice_preset_id", "groups", type_="foreignkey")
    op.drop_constraint("fk_groups_style_profile_id", "groups", type_="foreignkey")
    op.drop_constraint("fk_groups_render_preset_id", "groups", type_="foreignkey")
    op.drop_column("groups", "channel_dna")
    op.drop_column("groups", "narrator_voice_preset_id")
    op.drop_column("groups", "style_profile_id")
    op.drop_column("groups", "render_preset_id")
