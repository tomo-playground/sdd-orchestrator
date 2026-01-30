"""drop project_name from logs and scores

Revision ID: e839f66f1899
Revises: 42fc6b015f1a
Create Date: 2026-01-30 10:00:48.049212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e839f66f1899'
down_revision: Union[str, Sequence[str], None] = '42fc6b015f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop project_name from activity_logs
    op.drop_index('ix_activity_logs_project_name', table_name='activity_logs')
    op.drop_column('activity_logs', 'project_name')
    
    # Drop project_name from scene_quality_scores
    op.drop_index('ix_scene_quality_scores_project_name', table_name='scene_quality_scores')
    op.drop_column('scene_quality_scores', 'project_name')


def downgrade() -> None:
    # Add project_name back to scene_quality_scores
    op.add_column('scene_quality_scores', sa.Column('project_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.create_index('ix_scene_quality_scores_project_name', 'scene_quality_scores', ['project_name'], unique=False)
    
    # Add project_name back to activity_logs
    op.add_column('activity_logs', sa.Column('project_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    # Fill existing ones with storyboard title if possible? 
    # For downgrade we just care about schema.
    op.create_index('ix_activity_logs_project_name', 'activity_logs', ['project_name'], unique=False)
