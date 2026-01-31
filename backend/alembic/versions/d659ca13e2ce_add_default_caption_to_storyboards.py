"""add_default_caption_to_storyboards

Revision ID: d659ca13e2ce
Revises: ee73c749faa9
Create Date: 2026-01-31 18:00:21.293460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd659ca13e2ce'
down_revision: Union[str, Sequence[str], None] = 'ee73c749faa9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('storyboards', sa.Column('default_caption', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('storyboards', 'default_caption')
