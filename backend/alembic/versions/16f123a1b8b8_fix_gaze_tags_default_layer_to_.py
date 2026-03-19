"""fix gaze tags default_layer to EXPRESSION(7)

All gaze group tags had inconsistent default_layer values (0, 2, 3, 6, 8).
Gaze direction affects facial expression, so all should be LAYER_EXPRESSION(7).
This ensures the Phase 11 non-frontal gaze weight boost (1.25x) applies correctly.

Revision ID: 16f123a1b8b8
Revises: 14e63762812b
Create Date: 2026-02-20 10:27:34.915374

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "16f123a1b8b8"
down_revision: str | Sequence[str] | None = "14e63762812b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LAYER_EXPRESSION = 7


def upgrade() -> None:
    """Set all gaze group tags to LAYER_EXPRESSION(7)."""
    op.execute(
        f"UPDATE tags SET default_layer = {LAYER_EXPRESSION} "
        f"WHERE group_name = 'gaze' AND default_layer != {LAYER_EXPRESSION}"
    )


def downgrade() -> None:
    """No-op: original layer values were inconsistent, no safe rollback."""
    pass
