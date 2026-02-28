"""Drop channel_dna JSONB column from groups

Channel DNA (tone, target_audience, worldview, guidelines) 실사용 0건.
YAGNI 원칙에 따라 제거. 니즈 발생 시 Project 레벨에 재설계.

Revision ID: v4w5x6y7z8a9
Revises: u3v4w5x6y7z8
Create Date: 2026-02-28 12:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "v4w5x6y7z8a9"
down_revision = "g3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("groups", "channel_dna")


def downgrade() -> None:
    op.add_column("groups", sa.Column("channel_dna", JSONB(), nullable=True))
