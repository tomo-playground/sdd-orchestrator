"""FK RESTRICT policies + composite index for group/storyboard

Revision ID: a2b3c4d5e6f7
Revises: f0a1b2c3d4e5
Create Date: 2026-02-02 15:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: str | Sequence[str] | None = 'f0a1b2c3d4e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. storyboards.group_id: replace FK with RESTRICT
    op.drop_constraint('fk_storyboards_group_id', 'storyboards', type_='foreignkey')
    op.create_foreign_key(
        'fk_storyboards_group_id', 'storyboards', 'groups',
        ['group_id'], ['id'], ondelete='RESTRICT',
    )

    # 2. groups.project_id: add RESTRICT FK
    #    (original FK was created by create_table — drop by convention name)
    op.drop_constraint('groups_project_id_fkey', 'groups', type_='foreignkey')
    op.create_foreign_key(
        'fk_groups_project_id', 'groups', 'projects',
        ['project_id'], ['id'], ondelete='RESTRICT',
    )

    # 3. Composite index for group-scoped storyboard listing
    op.create_index(
        'ix_storyboards_group_created',
        'storyboards',
        ['group_id', sa.text('created_at DESC')],
    )


def downgrade() -> None:
    op.drop_index('ix_storyboards_group_created', table_name='storyboards')

    # Restore original FK without RESTRICT
    op.drop_constraint('fk_groups_project_id', 'groups', type_='foreignkey')
    op.create_foreign_key(
        'groups_project_id_fkey', 'groups', 'projects',
        ['project_id'], ['id'],
    )

    op.drop_constraint('fk_storyboards_group_id', 'storyboards', type_='foreignkey')
    op.create_foreign_key(
        'fk_storyboards_group_id', 'storyboards', 'groups',
        ['group_id'], ['id'],
    )
