"""creative_lab_v2_columns

Revision ID: 4c37698107e5
Revises: cdc167b32c1b
Create Date: 2026-02-09 12:16:18.200258

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c37698107e5"
down_revision: str | Sequence[str] | None = "cdc167b32c1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Creative Lab V2 columns to sessions and traces."""
    # creative_sessions — V2 fields
    op.add_column(
        "creative_sessions", sa.Column("session_type", sa.String(length=20), server_default="free", nullable=False)
    )
    op.add_column(
        "creative_sessions", sa.Column("director_mode", sa.String(length=20), server_default="advisor", nullable=False)
    )
    op.add_column(
        "creative_sessions", sa.Column("concept_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column("creative_sessions", sa.Column("selected_concept_index", sa.Integer(), nullable=True))

    # creative_traces — V2 fields
    op.add_column("creative_traces", sa.Column("phase", sa.String(length=20), nullable=True))
    op.add_column("creative_traces", sa.Column("step_name", sa.String(length=50), nullable=True))
    op.add_column("creative_traces", sa.Column("target_agent", sa.String(length=50), nullable=True))
    op.add_column(
        "creative_traces", sa.Column("decision_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column("creative_traces", sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))

    # Indexes for V2 queries
    op.create_index(
        "ix_creative_traces_phase_step", "creative_traces", ["session_id", "phase", "step_name"], unique=False
    )
    op.create_index("ix_creative_traces_target", "creative_traces", ["session_id", "target_agent"], unique=False)


def downgrade() -> None:
    """Remove Creative Lab V2 columns."""
    op.drop_index("ix_creative_traces_target", table_name="creative_traces")
    op.drop_index("ix_creative_traces_phase_step", table_name="creative_traces")
    op.drop_column("creative_traces", "retry_count")
    op.drop_column("creative_traces", "decision_context")
    op.drop_column("creative_traces", "target_agent")
    op.drop_column("creative_traces", "step_name")
    op.drop_column("creative_traces", "phase")
    op.drop_column("creative_sessions", "selected_concept_index")
    op.drop_column("creative_sessions", "concept_candidates")
    op.drop_column("creative_sessions", "director_mode")
    op.drop_column("creative_sessions", "session_type")
