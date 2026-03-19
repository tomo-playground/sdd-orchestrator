"""drop render_presets.project_id column

Revision ID: 502d0f4232de
Revises: d98cd7a8d450
Create Date: 2026-02-05 20:40:52.921567

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "502d0f4232de"
down_revision: str | Sequence[str] | None = "d98cd7a8d450"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("render_presets_project_id_fkey"), "render_presets", type_="foreignkey")
    op.drop_index(op.f("ix_render_presets_project_id"), table_name="render_presets")
    op.drop_column("render_presets", "project_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("render_presets", sa.Column("project_id", sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_index(op.f("ix_render_presets_project_id"), "render_presets", ["project_id"], unique=False)
    op.create_foreign_key(
        op.f("render_presets_project_id_fkey"), "render_presets", "projects", ["project_id"], ["id"], ondelete="CASCADE"
    )
