"""Add evaluation_details JSONB to scene_quality_scores

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-15

Phase 33: Stores hybrid evaluation breakdown (WD14 + Gemini results per tag).
"""

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op


def upgrade() -> None:
    op.add_column(
        "scene_quality_scores",
        sa.Column("evaluation_details", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scene_quality_scores", "evaluation_details")
