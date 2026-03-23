"""SP-073: Drop dead feature columns

Removes columns for 4 dead features:
- activity_logs: Gemini auto-edit tracking (gemini_edited, gemini_cost_usd, original_match_rate, final_match_rate)
- loras: calibration (optimal_weight, calibration_score), civitai import (civitai_id), gender lock (gender_locked)
- tags: thumbnail (thumbnail_asset_id)

Revision ID: sp073a0000001
Revises: sp056a1b2c3d4
Create Date: 2026-03-23
"""

import sqlalchemy as sa

from alembic import op

revision = "sp073a0000001"
down_revision = "sp056a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # activity_logs: Gemini auto-edit tracking
    op.drop_index("ix_activity_logs_gemini_edited", table_name="activity_logs")
    op.drop_column("activity_logs", "final_match_rate")
    op.drop_column("activity_logs", "original_match_rate")
    op.drop_column("activity_logs", "gemini_cost_usd")
    op.drop_column("activity_logs", "gemini_edited")

    # loras: calibration + civitai_id + gender_locked
    op.drop_index("idx_loras_civitai", table_name="loras")
    op.drop_column("loras", "calibration_score")
    op.drop_column("loras", "optimal_weight")
    op.drop_column("loras", "civitai_id")
    op.drop_column("loras", "gender_locked")

    # tags: thumbnail
    op.drop_constraint("fk_tags_thumbnail_asset_id", "tags", type_="foreignkey")
    op.drop_column("tags", "thumbnail_asset_id")


def downgrade() -> None:
    # tags: thumbnail
    op.add_column("tags", sa.Column("thumbnail_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tags_thumbnail_asset_id", "tags", "media_assets", ["thumbnail_asset_id"], ["id"], ondelete="SET NULL"
    )

    # loras
    op.add_column("loras", sa.Column("gender_locked", sa.String(10), nullable=True))
    op.add_column("loras", sa.Column("civitai_id", sa.Integer(), nullable=True))
    op.add_column("loras", sa.Column("optimal_weight", sa.Numeric(3, 2), nullable=True))
    op.add_column("loras", sa.Column("calibration_score", sa.Integer(), nullable=True))
    op.create_index("idx_loras_civitai", "loras", ["civitai_id"])

    # activity_logs
    op.add_column("activity_logs", sa.Column("gemini_edited", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("activity_logs", sa.Column("gemini_cost_usd", sa.Float(), nullable=True))
    op.add_column("activity_logs", sa.Column("original_match_rate", sa.Float(), nullable=True))
    op.add_column("activity_logs", sa.Column("final_match_rate", sa.Float(), nullable=True))
    op.create_index("ix_activity_logs_gemini_edited", "activity_logs", ["gemini_edited"])
