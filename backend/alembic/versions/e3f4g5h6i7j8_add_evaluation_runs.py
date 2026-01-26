"""add_evaluation_runs

Revision ID: e3f4g5h6i7j8
Revises: d2e3f4g5h6i7
Create Date: 2026-01-26 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3f4g5h6i7j8'
down_revision: str | Sequence[str] | None = 'd2e3f4g5h6i7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('evaluation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_name', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=True),
        sa.Column('character_name', sa.String(length=100), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('match_rate', sa.Float(), nullable=True),
        sa.Column('matched_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('missing_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extra_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('image_path', sa.String(length=500), nullable=True),
        sa.Column('seed', sa.Integer(), nullable=True),
        sa.Column('steps', sa.Integer(), nullable=True),
        sa.Column('cfg_scale', sa.Float(), nullable=True),
        sa.Column('batch_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluation_runs_test_name', 'evaluation_runs', ['test_name'], unique=False)
    op.create_index('ix_evaluation_runs_mode', 'evaluation_runs', ['mode'], unique=False)
    op.create_index('ix_evaluation_runs_character_id', 'evaluation_runs', ['character_id'], unique=False)
    op.create_index('ix_evaluation_runs_batch_id', 'evaluation_runs', ['batch_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_evaluation_runs_batch_id', table_name='evaluation_runs')
    op.drop_index('ix_evaluation_runs_character_id', table_name='evaluation_runs')
    op.drop_index('ix_evaluation_runs_mode', table_name='evaluation_runs')
    op.drop_index('ix_evaluation_runs_test_name', table_name='evaluation_runs')
    op.drop_table('evaluation_runs')
