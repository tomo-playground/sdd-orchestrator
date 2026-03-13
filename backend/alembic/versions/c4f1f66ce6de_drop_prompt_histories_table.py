"""Drop prompt_histories table

Remove the prompt_histories table which is no longer used.
The /library/prompts feature has been removed.

Revision ID: c4f1f66ce6de
Revises: z8a9b0c1d2e3
Create Date: 2026-03-13 12:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c4f1f66ce6de"
down_revision = "z8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prompt_histories")


def downgrade() -> None:
    op.create_table(
        "prompt_histories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("character_id", sa.Integer(), nullable=True, index=True),
        sa.Column("positive_prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("steps", sa.Integer(), server_default="20"),
        sa.Column("cfg_scale", sa.Float(), server_default="7.0"),
        sa.Column("sampler_name", sa.String(50), nullable=True),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("clip_skip", sa.Integer(), server_default="2"),
        sa.Column("lora_settings", postgresql.JSONB(), nullable=True),
        sa.Column("context_tags", postgresql.JSONB(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default="false"),
        sa.Column("use_count", sa.Integer(), server_default="1"),
        sa.Column("last_match_rate", sa.Float(), nullable=True),
        sa.Column("avg_match_rate", sa.Float(), nullable=True),
        sa.Column("validation_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
