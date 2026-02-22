"""Drop unused columns: scenes.description, creative_traces.diff_summary

scenes.description: 929행 전부 빈 값 (미구현 기능, image_prompt로 대체됨)
creative_traces.diff_summary: 1,962행 전부 NULL (V2 필드로 대체된 Dead Code)

Revision ID: n1g2h3i4j5k6
Revises: m0f1g2h3i4j5
Create Date: 2026-02-22 15:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "n1g2h3i4j5k6"
down_revision = "m0f1g2h3i4j5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("scenes", "description")
    op.drop_column("creative_traces", "diff_summary")


def downgrade() -> None:
    op.add_column("creative_traces", sa.Column("diff_summary", sa.Text(), nullable=True))
    op.add_column("scenes", sa.Column("description", sa.Text(), nullable=True))
