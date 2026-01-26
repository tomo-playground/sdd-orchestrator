"""add_lora_gender_locked

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-24 17:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: str | Sequence[str] | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add gender_locked column to loras."""
    op.add_column(
        'loras',
        sa.Column('gender_locked', sa.String(10), nullable=True)
    )


def downgrade() -> None:
    """Remove gender_locked column."""
    op.drop_column('loras', 'gender_locked')
