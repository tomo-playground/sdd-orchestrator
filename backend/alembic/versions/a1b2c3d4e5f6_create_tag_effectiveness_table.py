"""create tag_effectiveness table

Revision ID: a1b2c3d4e5f6
Revises: 2028041a8e51
Create Date: 2026-02-01 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '2028041a8e51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tag_effectiveness table for per-tag prompt effectiveness tracking."""
    op.create_table(
        'tag_effectiveness',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tags.id', ondelete='CASCADE'), nullable=False),
        sa.Column('use_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('match_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('effectiveness', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_tag_effectiveness_tag_id', 'tag_effectiveness', ['tag_id'])
    op.create_unique_constraint('uq_tag_effectiveness_tag_id', 'tag_effectiveness', ['tag_id'])


def downgrade() -> None:
    """Drop tag_effectiveness table."""
    op.drop_table('tag_effectiveness')
