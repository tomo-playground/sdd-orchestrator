"""create_lab_experiments

Revision ID: fda928418f15
Revises: 3e630c03fb72
Create Date: 2026-02-07 19:54:37.925192

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fda928418f15"
down_revision: str | Sequence[str] | None = "3e630c03fb72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create lab_experiments table.

    Uses if_not_exists because Base.metadata.create_all() may have
    already created the table before this migration runs.
    """
    # Check if table already exists (created by create_all)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "lab_experiments" in inspector.get_table_names():
        return

    op.create_table(
        "lab_experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.String(50), nullable=True, index=True),
        sa.Column("experiment_type", sa.String(20), nullable=False, server_default="tag_render", index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prompt_used", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("target_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sd_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("media_asset_id", sa.Integer(), sa.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("match_rate", sa.Float(), nullable=True, index=True),
        sa.Column("wd14_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scene_description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    """Drop lab_experiments table."""
    op.drop_table("lab_experiments")
