"""Move SD generation settings from scenes to group_config.

Adds sd_steps, sd_cfg_scale, sd_sampler_name, sd_clip_skip to group_config.
Removes steps, cfg_scale, sampler_name, seed, clip_skip from scenes.

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-02-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m7n8o9p0q1r2"
down_revision: str | Sequence[str] | None = "l6m7n8o9p0q1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add SD settings columns to group_config
    op.add_column("group_config", sa.Column("sd_steps", sa.Integer(), nullable=True))
    op.add_column("group_config", sa.Column("sd_cfg_scale", sa.Float(), nullable=True))
    op.add_column("group_config", sa.Column("sd_sampler_name", sa.String(50), nullable=True))
    op.add_column("group_config", sa.Column("sd_clip_skip", sa.Integer(), nullable=True))

    # Remove SD settings columns from scenes
    op.drop_column("scenes", "steps")
    op.drop_column("scenes", "cfg_scale")
    op.drop_column("scenes", "sampler_name")
    op.drop_column("scenes", "seed")
    op.drop_column("scenes", "clip_skip")


def downgrade() -> None:
    # Re-add SD settings columns to scenes
    op.add_column("scenes", sa.Column("steps", sa.Integer(), nullable=True))
    op.add_column("scenes", sa.Column("cfg_scale", sa.Float(), nullable=True))
    op.add_column("scenes", sa.Column("sampler_name", sa.String(50), nullable=True))
    op.add_column("scenes", sa.Column("seed", sa.BigInteger(), nullable=True))
    op.add_column("scenes", sa.Column("clip_skip", sa.Integer(), nullable=True))

    # Remove SD settings columns from group_config
    op.drop_column("group_config", "sd_steps")
    op.drop_column("group_config", "sd_cfg_scale")
    op.drop_column("group_config", "sd_sampler_name")
    op.drop_column("group_config", "sd_clip_skip")
