"""drop_project_dead_columns

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-02-05

Drop dead cascading FK columns and unused avatar_asset_id from projects.
GroupConfig is the SSOT for render_preset_id, character_id, style_profile_id.
avatar_asset_id was never written in production (always NULL).
"""

import sqlalchemy as sa

from alembic import op

revision = "x8y9z0a1b2c3"
down_revision = "w7x8y9z0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK constraints first
    op.drop_constraint("fk_projects_avatar_asset_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_render_preset_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_default_character_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_default_style_profile_id", "projects", type_="foreignkey")

    # Drop columns
    op.drop_column("projects", "avatar_asset_id")
    op.drop_column("projects", "render_preset_id")
    op.drop_column("projects", "character_id")
    op.drop_column("projects", "style_profile_id")


def downgrade() -> None:
    # Re-add columns
    op.add_column(
        "projects",
        sa.Column("avatar_asset_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("render_preset_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("character_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("style_profile_id", sa.Integer(), nullable=True),
    )

    # Re-add FK constraints
    op.create_foreign_key(
        "fk_projects_avatar_asset_id",
        "projects",
        "media_assets",
        ["avatar_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_projects_render_preset_id",
        "projects",
        "render_presets",
        ["render_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_projects_default_character_id",
        "projects",
        "characters",
        ["character_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_projects_default_style_profile_id",
        "projects",
        "style_profiles",
        ["style_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
