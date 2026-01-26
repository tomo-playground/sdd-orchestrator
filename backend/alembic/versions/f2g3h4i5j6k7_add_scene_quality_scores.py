"""add_scene_quality_scores

Revision ID: f2g3h4i5j6k7
Revises: e3f4g5h6i7j8
Create Date: 2026-01-28 02:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2g3h4i5j6k7'
down_revision: str | Sequence[str] | None = 'e3f4g5h6i7j8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('scene_quality_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_name', sa.String(length=200), nullable=False),
        sa.Column('scene_id', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('match_rate', sa.Float(), nullable=True),
        sa.Column('matched_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('missing_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extra_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scene_quality_project', 'scene_quality_scores', ['project_name'], unique=False)
    op.create_index('ix_scene_quality_match_rate', 'scene_quality_scores', ['match_rate'], unique=False)
    op.create_index('ix_scene_quality_scene_id', 'scene_quality_scores', ['scene_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_scene_quality_scene_id', table_name='scene_quality_scores')
    op.drop_index('ix_scene_quality_match_rate', table_name='scene_quality_scores')
    op.drop_index('ix_scene_quality_project', table_name='scene_quality_scores')
    op.drop_table('scene_quality_scores')
