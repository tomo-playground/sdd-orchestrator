"""Add cascading config FKs to projects and groups

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-02 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- projects table: 3 FK columns --

    # 1. render_preset_id
    op.add_column("projects", sa.Column("render_preset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_render_preset_id",
        "projects",
        "render_presets",
        ["render_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_render_preset_id", "projects", ["render_preset_id"])

    # 2. default_character_id
    op.add_column("projects", sa.Column("default_character_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_default_character_id",
        "projects",
        "characters",
        ["default_character_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_default_character_id", "projects", ["default_character_id"])

    # 3. default_style_profile_id
    op.add_column("projects", sa.Column("default_style_profile_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_default_style_profile_id",
        "projects",
        "style_profiles",
        ["default_style_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_default_style_profile_id", "projects", ["default_style_profile_id"])

    # -- groups table: 2 FK columns --

    # 4. default_character_id
    op.add_column("groups", sa.Column("default_character_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_groups_default_character_id",
        "groups",
        "characters",
        ["default_character_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_groups_default_character_id", "groups", ["default_character_id"])

    # 5. default_style_profile_id
    op.add_column("groups", sa.Column("default_style_profile_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_groups_default_style_profile_id",
        "groups",
        "style_profiles",
        ["default_style_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_groups_default_style_profile_id", "groups", ["default_style_profile_id"])


def downgrade() -> None:
    # -- groups table: drop in reverse order --

    # 5. default_style_profile_id
    op.drop_index("ix_groups_default_style_profile_id", table_name="groups")
    op.drop_constraint("fk_groups_default_style_profile_id", "groups", type_="foreignkey")
    op.drop_column("groups", "default_style_profile_id")

    # 4. default_character_id
    op.drop_index("ix_groups_default_character_id", table_name="groups")
    op.drop_constraint("fk_groups_default_character_id", "groups", type_="foreignkey")
    op.drop_column("groups", "default_character_id")

    # -- projects table: drop in reverse order --

    # 3. default_style_profile_id
    op.drop_index("ix_projects_default_style_profile_id", table_name="projects")
    op.drop_constraint("fk_projects_default_style_profile_id", "projects", type_="foreignkey")
    op.drop_column("projects", "default_style_profile_id")

    # 2. default_character_id
    op.drop_index("ix_projects_default_character_id", table_name="projects")
    op.drop_constraint("fk_projects_default_character_id", "projects", type_="foreignkey")
    op.drop_column("projects", "default_character_id")

    # 1. render_preset_id
    op.drop_index("ix_projects_render_preset_id", table_name="projects")
    op.drop_constraint("fk_projects_render_preset_id", "projects", type_="foreignkey")
    op.drop_column("projects", "render_preset_id")
