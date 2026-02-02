"""Character global scope: nullable project_id, global name unique

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-02-02 23:01:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: str = 'c1d2e3f4a5b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint('uq_characters_project_name', 'characters', type_='unique')
    op.drop_constraint('fk_characters_project_id', 'characters', type_='foreignkey')
    op.alter_column('characters', 'project_id', nullable=True)
    op.create_foreign_key(
        'fk_characters_project_id', 'characters', 'projects',
        ['project_id'], ['id'], ondelete='SET NULL',
    )
    op.create_unique_constraint('uq_characters_name', 'characters', ['name'])


def downgrade() -> None:
    op.drop_constraint('uq_characters_name', 'characters', type_='unique')
    op.drop_constraint('fk_characters_project_id', 'characters', type_='foreignkey')
    op.alter_column('characters', 'project_id', nullable=False)
    op.create_foreign_key(
        'fk_characters_project_id', 'characters', 'projects',
        ['project_id'], ['id'], ondelete='RESTRICT',
    )
    op.create_unique_constraint('uq_characters_project_name', 'characters', ['project_id', 'name'])
