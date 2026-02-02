"""Add characters.project_id FK + composite unique constraint

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-02 15:10:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: str | Sequence[str] | None = 'a2b3c4d5e6f7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add project_id as nullable first
    op.add_column('characters', sa.Column('project_id', sa.Integer, nullable=True))

    # 2. Migrate existing characters to project 1
    op.execute(text("UPDATE characters SET project_id = 1 WHERE project_id IS NULL"))

    # 3. Make NOT NULL
    op.alter_column('characters', 'project_id', nullable=False)

    # 4. Add FK with RESTRICT
    op.create_foreign_key(
        'fk_characters_project_id', 'characters', 'projects',
        ['project_id'], ['id'], ondelete='RESTRICT',
    )

    # 5. Drop old unique constraint on name
    op.drop_constraint('characters_name_key', 'characters', type_='unique')

    # 6. Add composite unique (project_id, name)
    op.create_unique_constraint(
        'uq_characters_project_name', 'characters',
        ['project_id', 'name'],
    )

    # 7. Index for project_id lookups
    op.create_index('ix_characters_project_id', 'characters', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_characters_project_id', table_name='characters')
    op.drop_constraint('uq_characters_project_name', 'characters', type_='unique')
    op.create_unique_constraint('characters_name_key', 'characters', ['name'])
    op.drop_constraint('fk_characters_project_id', 'characters', type_='foreignkey')
    op.drop_column('characters', 'project_id')
