"""merge_two_heads

Revision ID: 1ccf182e0f06
Revises: 876d46988906, w5x6y7z8a9b0
Create Date: 2026-03-01 09:44:32.670530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ccf182e0f06'
down_revision: Union[str, Sequence[str], None] = ('876d46988906', 'w5x6y7z8a9b0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
