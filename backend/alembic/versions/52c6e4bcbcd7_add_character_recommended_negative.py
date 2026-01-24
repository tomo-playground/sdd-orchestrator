"""add_character_recommended_negative

Revision ID: 52c6e4bcbcd7
Revises: 66645c47c203
Create Date: 2026-01-24 15:23:11.609231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52c6e4bcbcd7'
down_revision: Union[str, Sequence[str], None] = '66645c47c203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add recommended_negative column to characters."""
    op.add_column(
        'characters',
        sa.Column('recommended_negative', sa.ARRAY(sa.Text), nullable=True)
    )


def downgrade() -> None:
    """Remove recommended_negative column."""
    op.drop_column('characters', 'recommended_negative')
