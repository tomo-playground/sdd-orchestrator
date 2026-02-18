"""Add group_id and V3 metadata to lab_experiments

Revision ID: 746fbdbee6ea
Revises: 1f854475bc89
Create Date: 2026-02-08 11:57:38.114655

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '746fbdbee6ea'
down_revision: str | Sequence[str] | None = '1f854475bc89'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add columns (group_id nullable first for data migration)
    op.add_column('lab_experiments', sa.Column('group_id', sa.Integer(), nullable=True))
    op.add_column('lab_experiments', sa.Column('final_prompt', sa.Text(), nullable=True))
    op.add_column('lab_experiments', sa.Column('loras_applied', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 2. Migrate existing data: character → project → first group in project
    op.execute("""
        UPDATE lab_experiments le
        SET group_id = (
            SELECT g.id
            FROM characters c
            JOIN groups g ON g.project_id = c.project_id
            WHERE c.id = le.character_id
            ORDER BY g.created_at
            LIMIT 1
        )
        WHERE le.character_id IS NOT NULL
          AND le.group_id IS NULL
    """)

    # 3. Delete experiments that can't be migrated (no character_id = no group)
    # Note: User confirmed existing data is test data and can be deleted
    op.execute("""
        DELETE FROM lab_experiments
        WHERE group_id IS NULL
    """)

    # 4. Make group_id NOT NULL
    op.alter_column('lab_experiments', 'group_id', nullable=False)

    # 5. Add FK constraint
    op.create_foreign_key(
        'fk_lab_experiments_group_id',
        'lab_experiments', 'groups',
        ['group_id'], ['id'],
        ondelete='CASCADE'
    )

    # 6. Add indexes for Analytics
    op.create_index('idx_lab_experiments_group_id', 'lab_experiments', ['group_id'])
    op.create_index('idx_lab_experiments_group_status', 'lab_experiments', ['group_id', 'status'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove indexes
    op.drop_index('idx_lab_experiments_group_status', table_name='lab_experiments')
    op.drop_index('idx_lab_experiments_group_id', table_name='lab_experiments')

    # Remove FK constraint
    op.drop_constraint('fk_lab_experiments_group_id', 'lab_experiments', type_='foreignkey')

    # Remove columns
    op.drop_column('lab_experiments', 'loras_applied')
    op.drop_column('lab_experiments', 'final_prompt')
    op.drop_column('lab_experiments', 'group_id')
