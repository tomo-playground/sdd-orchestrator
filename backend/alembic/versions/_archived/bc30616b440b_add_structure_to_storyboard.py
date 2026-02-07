"""add_structure_to_storyboard

Revision ID: bc30616b440b
Revises: y9z0a1b2c3d4
Create Date: 2026-02-06 09:03:33.583661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc30616b440b'
down_revision: Union[str, Sequence[str], None] = 'y9z0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add structure column to storyboards."""
    op.add_column(
        'storyboards',
        sa.Column('structure', sa.String(length=50), nullable=False, server_default='Monologue')
    )


def downgrade() -> None:
    """Remove structure column from storyboards."""
    op.drop_column('storyboards', 'structure')
