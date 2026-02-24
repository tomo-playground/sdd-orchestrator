"""add_identity_columns_to_scene_quality_scores

Revision ID: 0a56f0c8f54a
Revises: q4j5k6l7m8n9
Create Date: 2026-02-24 19:41:20.744967

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a56f0c8f54a"
down_revision: str | Sequence[str] | None = "q4j5k6l7m8n9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scene_quality_scores", sa.Column("identity_score", sa.Float(), nullable=True))
    op.add_column("scene_quality_scores", sa.Column("identity_tags_detected", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("scene_quality_scores", "identity_tags_detected")
    op.drop_column("scene_quality_scores", "identity_score")
