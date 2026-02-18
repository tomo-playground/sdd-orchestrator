"""add_leader_direction_to_rounds

Revision ID: a3b4c5d6e7f8
Revises: 2f427f06a4b4
Create Date: 2026-02-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "2f427f06a4b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "creative_session_rounds" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("creative_session_rounds")]
        if "leader_direction" not in columns:
            op.add_column(
                "creative_session_rounds",
                sa.Column("leader_direction", sa.Text(), nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "creative_session_rounds" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("creative_session_rounds")]
        if "leader_direction" in columns:
            op.drop_column("creative_session_rounds", "leader_direction")
