"""drop_evaluation_runs

Revision ID: 3e630c03fb72
Revises: fb07a1c2d3e4
Create Date: 2026-02-07 19:36:14.067290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3e630c03fb72'
down_revision: Union[str, Sequence[str], None] = 'fb07a1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop evaluation_runs table (legacy evaluation system removed)."""
    op.drop_index(op.f('ix_evaluation_runs_batch_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_character_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_match_rate'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_mode'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_test_name'), table_name='evaluation_runs')
    op.drop_table('evaluation_runs')


def downgrade() -> None:
    """Recreate evaluation_runs table."""
    op.create_table('evaluation_runs',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        sa.Column('test_name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('mode', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
        sa.Column('character_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('character_name', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.Column('prompt_used', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('negative_prompt', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('seed', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('steps', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('cfg_scale', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column('match_rate', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('matched_tags', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('missing_tags', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('extra_tags', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('evaluation_runs_pkey'))
    )
    op.create_index(op.f('ix_evaluation_runs_test_name'), 'evaluation_runs', ['test_name'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_mode'), 'evaluation_runs', ['mode'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_match_rate'), 'evaluation_runs', ['match_rate'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_character_id'), 'evaluation_runs', ['character_id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_batch_id'), 'evaluation_runs', ['batch_id'], unique=False)
