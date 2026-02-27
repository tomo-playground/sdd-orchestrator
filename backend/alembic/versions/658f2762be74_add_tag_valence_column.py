"""add tag valence column

Revision ID: 658f2762be74
Revises: u3v4w5x6y7z8
Create Date: 2026-02-27 22:27:23.357619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '658f2762be74'
down_revision: Union[str, Sequence[str], None] = 'u3v4w5x6y7z8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add valence column to tags table."""
    op.add_column('tags', sa.Column('valence', sa.String(length=10), nullable=True))
    op.create_index(op.f('ix_tags_valence'), 'tags', ['valence'], unique=False)


def downgrade() -> None:
    """Remove valence column from tags table."""
    op.drop_index(op.f('ix_tags_valence'), table_name='tags')
    op.drop_column('tags', 'valence')
