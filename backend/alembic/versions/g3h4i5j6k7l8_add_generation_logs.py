"""add_generation_logs

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2026-01-28 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, Sequence[str], None] = 'f2g3h4i5j6k7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('generation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_name', sa.String(length=200), nullable=False),
        sa.Column('scene_index', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sd_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('match_rate', sa.Float(), nullable=True),
        sa.Column('seed', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_generation_logs_project', 'generation_logs', ['project_name'], unique=False)
    op.create_index('ix_generation_logs_status', 'generation_logs', ['status'], unique=False)
    op.create_index('ix_generation_logs_match_rate', 'generation_logs', ['match_rate'], unique=False)
    op.create_index('ix_generation_logs_scene_index', 'generation_logs', ['scene_index'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_generation_logs_scene_index', table_name='generation_logs')
    op.drop_index('ix_generation_logs_match_rate', table_name='generation_logs')
    op.drop_index('ix_generation_logs_status', table_name='generation_logs')
    op.drop_index('ix_generation_logs_project', table_name='generation_logs')
    op.drop_table('generation_logs')
