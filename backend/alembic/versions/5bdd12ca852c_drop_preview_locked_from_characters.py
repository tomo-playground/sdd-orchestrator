"""drop preview_locked from characters

Revision ID: 5bdd12ca852c
Revises: v4w5x6y7z8a9
Create Date: 2026-02-28 16:53:47.665761

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5bdd12ca852c"
down_revision: str | Sequence[str] | None = "v4w5x6y7z8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("characters", "preview_locked")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "characters",
        sa.Column("preview_locked", sa.BOOLEAN(), server_default=sa.text("false"), autoincrement=False, nullable=False),
    )
