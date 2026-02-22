"""Fix render_presets.bgm_mode NULL rows → 'manual' default + NOT NULL

기존 3행 전부 NULL → 'manual'로 UPDATE 후 server_default + NOT NULL 적용.

Revision ID: o2h3i4j5k6l7
Revises: n1g2h3i4j5k6
Create Date: 2026-02-22 18:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "o2h3i4j5k6l7"
down_revision = "n1g2h3i4j5k6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE render_presets SET bgm_mode = 'manual' WHERE bgm_mode IS NULL")
    op.alter_column(
        "render_presets",
        "bgm_mode",
        existing_type=sa.String(20),
        server_default="manual",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "render_presets",
        "bgm_mode",
        existing_type=sa.String(20),
        server_default=None,
        nullable=True,
    )
