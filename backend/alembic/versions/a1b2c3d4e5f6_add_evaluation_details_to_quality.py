"""Add evaluation_details JSONB to scene_quality_scores

Revision ID: a1b2c3d4e5f6
Revises: z8a9b0c1d2e3
Create Date: 2026-03-15

Phase 33: Stores hybrid evaluation breakdown (WD14 + Gemini results per tag).
"""

revision = "a1b2c3d4e5f6"
down_revision = "z8a9b0c1d2e3"

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
