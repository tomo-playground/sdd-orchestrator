"""Remove SD generation params from group_config.

SD parameters (steps, cfg_scale, sampler_name, clip_skip) were only used for
Preflight display, not actual image generation. The actual SSOT is
StyleProfile.default_* fields. Removing to eliminate confusion.

Revision ID: f2g3h4i5j6k7
Revises: e1b2c3d4f5g6
Create Date: 2026-02-28

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f2g3h4i5j6k7"
down_revision = "e1b2c3d4f5g6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("group_config", "sd_steps")
    op.drop_column("group_config", "sd_cfg_scale")
    op.drop_column("group_config", "sd_sampler_name")
    op.drop_column("group_config", "sd_clip_skip")


def downgrade() -> None:
    op.add_column(
        "group_config",
        sa.Column("sd_clip_skip", sa.Integer(), nullable=True),
    )
    op.add_column(
        "group_config",
        sa.Column("sd_sampler_name", sa.String(50), nullable=True),
    )
    op.add_column(
        "group_config",
        sa.Column("sd_cfg_scale", sa.Float(), nullable=True),
    )
    op.add_column(
        "group_config",
        sa.Column("sd_steps", sa.Integer(), nullable=True),
    )
