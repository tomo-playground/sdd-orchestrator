"""Change prompt_histories.seed from Integer to BigInteger

SD WebUI seeds can be up to 2^32-1 (4294967295), which exceeds
the Integer limit of 2^31-1 (2147483647). BigInteger supports
values up to 2^63-1, safely covering the full seed range.

Revision ID: r5k6l7m8n9o0
Revises: e684c36207f5
Create Date: 2026-02-26 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "r5k6l7m8n9o0"
down_revision = "e684c36207f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "prompt_histories",
        "seed",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "prompt_histories",
        "seed",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
