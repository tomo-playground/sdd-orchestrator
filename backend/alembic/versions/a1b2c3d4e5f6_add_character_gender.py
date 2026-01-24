"""add_character_gender

Revision ID: a1b2c3d4e5f6
Revises: 52c6e4bcbcd7
Create Date: 2026-01-24 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '52c6e4bcbcd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add gender column to characters."""
    op.add_column(
        'characters',
        sa.Column('gender', sa.String(10), nullable=True)
    )


def downgrade() -> None:
    """Remove gender column."""
    op.drop_column('characters', 'gender')
