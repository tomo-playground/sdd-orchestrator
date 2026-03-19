"""drop reference_source_type and last_seed columns

Revision ID: 136a62ea8e04
Revises: 658f2762be74
Create Date: 2026-02-28 01:09:43.307185

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "136a62ea8e04"
down_revision: str | Sequence[str] | None = "658f2762be74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop unused columns: characters.reference_source_type, scenes.last_seed."""
    op.drop_constraint("ck_characters_reference_source_type", "characters", type_="check")
    op.drop_column("characters", "reference_source_type")
    op.drop_column("scenes", "last_seed")


def downgrade() -> None:
    """Restore dropped columns."""
    op.add_column("scenes", sa.Column("last_seed", sa.BIGINT(), autoincrement=False, nullable=True))
    op.add_column(
        "characters", sa.Column("reference_source_type", sa.VARCHAR(length=20), autoincrement=False, nullable=True)
    )
    op.create_check_constraint(
        "ck_characters_reference_source_type",
        "characters",
        "reference_source_type IN ('generated', 'uploaded')",
    )
