"""Extend scene columns for full frontend mapping

Revision ID: b1f2a3c4d5e6
Revises: 4bd92b46246d
Create Date: 2026-01-30 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1f2a3c4d5e6'
down_revision: str | None = '4bd92b46246d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('scenes', sa.Column('speaker', sa.String(20), server_default='Narrator'))
    op.add_column('scenes', sa.Column('duration', sa.Float(), server_default='3.0'))
    op.add_column('scenes', sa.Column('image_prompt', sa.Text()))
    op.add_column('scenes', sa.Column('image_prompt_ko', sa.Text()))
    op.add_column('scenes', sa.Column('negative_prompt', sa.Text()))
    op.add_column('scenes', sa.Column('steps', sa.Integer()))
    op.add_column('scenes', sa.Column('cfg_scale', sa.Float()))
    op.add_column('scenes', sa.Column('sampler_name', sa.String(50)))
    op.add_column('scenes', sa.Column('seed', sa.BigInteger()))
    op.add_column('scenes', sa.Column('clip_skip', sa.Integer()))
    op.add_column('scenes', sa.Column('context_tags', postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column('scenes', 'context_tags')
    op.drop_column('scenes', 'clip_skip')
    op.drop_column('scenes', 'seed')
    op.drop_column('scenes', 'sampler_name')
    op.drop_column('scenes', 'cfg_scale')
    op.drop_column('scenes', 'steps')
    op.drop_column('scenes', 'negative_prompt')
    op.drop_column('scenes', 'image_prompt_ko')
    op.drop_column('scenes', 'image_prompt')
    op.drop_column('scenes', 'duration')
    op.drop_column('scenes', 'speaker')
