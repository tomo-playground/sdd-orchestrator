"""group_defaults_cleanup

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-02-04

Group Defaults (7-2 #1.7):
- Add character_id FK to group_config
- Migrate render_preset_id, style_profile_id from groups → group_config
- DROP render_preset_id, style_profile_id from groups
"""

import sqlalchemy as sa

from alembic import op

revision = "r2s3t4u5v6w7"
down_revision = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add character_id to group_config
    op.add_column(
        "group_config",
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="SET NULL"), nullable=True),
    )

    # 2. Migrate groups.render_preset_id → group_config (where group_config exists and value is NULL)
    op.execute("""
        UPDATE group_config gc
        SET render_preset_id = g.render_preset_id
        FROM groups g
        WHERE gc.group_id = g.id
          AND gc.render_preset_id IS NULL
          AND g.render_preset_id IS NOT NULL
    """)

    # 3. Migrate groups.style_profile_id → group_config (where group_config exists and value is NULL)
    op.execute("""
        UPDATE group_config gc
        SET style_profile_id = g.style_profile_id
        FROM groups g
        WHERE gc.group_id = g.id
          AND gc.style_profile_id IS NULL
          AND g.style_profile_id IS NOT NULL
    """)

    # 4. Create group_config rows for groups that don't have one yet, copying values
    op.execute("""
        INSERT INTO group_config (group_id, render_preset_id, style_profile_id)
        SELECT g.id, g.render_preset_id, g.style_profile_id
        FROM groups g
        LEFT JOIN group_config gc ON gc.group_id = g.id
        WHERE gc.id IS NULL
          AND (g.render_preset_id IS NOT NULL OR g.style_profile_id IS NOT NULL)
    """)

    # 5. DROP columns from groups
    op.drop_constraint("fk_groups_render_preset_id", "groups", type_="foreignkey")
    op.drop_column("groups", "render_preset_id")
    op.drop_constraint("fk_groups_default_style_profile_id", "groups", type_="foreignkey")
    op.drop_column("groups", "style_profile_id")


def downgrade() -> None:
    # Re-add columns to groups
    op.add_column(
        "groups",
        sa.Column(
            "render_preset_id", sa.Integer(), sa.ForeignKey("render_presets.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.add_column(
        "groups",
        sa.Column(
            "style_profile_id", sa.Integer(), sa.ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True
        ),
    )

    # Copy back from group_config
    op.execute("""
        UPDATE groups g
        SET render_preset_id = gc.render_preset_id,
            style_profile_id = gc.style_profile_id
        FROM group_config gc
        WHERE gc.group_id = g.id
    """)

    # Drop character_id from group_config
    op.drop_column("group_config", "character_id")
