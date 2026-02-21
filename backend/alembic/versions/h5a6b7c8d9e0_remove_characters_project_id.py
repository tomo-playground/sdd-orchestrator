"""Remove characters.project_id column

project_id was unused — characters are globally scoped with unique name constraint.

Revision ID: h5a6b7c8d9e0
Revises: g4b5c6d7e8f9
Create Date: 2026-02-21 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "h5a6b7c8d9e0"
down_revision = "g4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_characters_project_id", "characters", type_="foreignkey")
    op.drop_column("characters", "project_id")


def downgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_characters_project_id",
        "characters",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
