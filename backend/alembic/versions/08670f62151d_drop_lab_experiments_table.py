"""drop lab_experiments table

Revision ID: 08670f62151d
Revises: c4f1f66ce6de
Create Date: 2026-03-13 21:20:47.334061

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '08670f62151d'
down_revision: str | Sequence[str] | None = 'c4f1f66ce6de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop lab_experiments table."""
    op.drop_table('lab_experiments')


def downgrade() -> None:
    """Recreate lab_experiments table (original + V3 columns)."""
    op.create_table(
        'lab_experiments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('batch_id', sa.String(50), nullable=True),
        sa.Column('experiment_type', sa.String(20), nullable=False, server_default='tag_render'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('final_prompt', sa.Text(), nullable=True),
        sa.Column('target_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sd_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('loras_applied', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('media_asset_id', sa.Integer(), sa.ForeignKey('media_assets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('seed', sa.BigInteger(), nullable=True),
        sa.Column('match_rate', sa.Float(), nullable=True),
        sa.Column('wd14_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scene_description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
    )

    # Recreate indexes
    op.create_index('ix_lab_experiments_batch_id', 'lab_experiments', ['batch_id'])
    op.create_index('ix_lab_experiments_experiment_type', 'lab_experiments', ['experiment_type'])
    op.create_index('ix_lab_experiments_match_rate', 'lab_experiments', ['match_rate'])
    op.create_index('idx_lab_experiments_group_id', 'lab_experiments', ['group_id'])
    op.create_index('idx_lab_experiments_group_status', 'lab_experiments', ['group_id', 'status'])
