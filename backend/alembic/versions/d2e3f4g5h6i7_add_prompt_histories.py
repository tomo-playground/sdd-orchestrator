"""add_prompt_histories

Revision ID: d2e3f4g5h6i7
Revises: c1fe90c80b65
Create Date: 2026-01-25 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2e3f4g5h6i7'
down_revision: str | Sequence[str] | None = 'c1fe90c80b65'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('prompt_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('positive_prompt', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('steps', sa.Integer(), nullable=True),
        sa.Column('cfg_scale', sa.Float(), nullable=True),
        sa.Column('sampler_name', sa.String(length=100), nullable=True),
        sa.Column('seed', sa.Integer(), nullable=True),
        sa.Column('clip_skip', sa.Integer(), nullable=True),
        sa.Column('character_id', sa.Integer(), nullable=True),
        sa.Column('lora_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_match_rate', sa.Float(), nullable=True),
        sa.Column('avg_match_rate', sa.Float(), nullable=True),
        sa.Column('validation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('preview_image_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prompt_histories_is_favorite', 'prompt_histories', ['is_favorite'], unique=False)
    op.create_index('ix_prompt_histories_character_id', 'prompt_histories', ['character_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_prompt_histories_character_id', table_name='prompt_histories')
    op.drop_index('ix_prompt_histories_is_favorite', table_name='prompt_histories')
    op.drop_table('prompt_histories')
