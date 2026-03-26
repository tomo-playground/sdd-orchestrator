"""merge sp021 and sp075 heads

Revision ID: d4d359f86412
Revises: sp021a1b2c3d4, sp075a0000001
Create Date: 2026-03-25 09:35:10.334656

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d4d359f86412"
down_revision: str | Sequence[str] | None = ("sp021a1b2c3d4", "sp075a0000001")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
