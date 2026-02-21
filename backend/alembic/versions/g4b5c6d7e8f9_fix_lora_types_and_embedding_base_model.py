"""Fix LoRA types (pose→style) and add Embedding base_model.

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-02-21
"""

import sqlalchemy as sa

from alembic import op

revision = "g4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None

# LoRA lora_type corrections: pose/misclassified → style
LORA_TYPE_FIXES = {
    "chibi-laugh": "style",
    "J_huiben": "style",
    "ghibli_style_offset": "style",
}


def upgrade() -> None:
    # 1. Fix LoRA lora_type: pose → style for misclassified entries
    loras = sa.table(
        "loras",
        sa.column("name", sa.String),
        sa.column("lora_type", sa.String),
        sa.column("base_model", sa.String),
    )
    for lora_name, correct_type in LORA_TYPE_FIXES.items():
        op.execute(loras.update().where(loras.c.name == lora_name).values(lora_type=correct_type))

    # 2. Fill LoRA base_model: null → SD1.5 (all current LoRAs are SD1.5)
    op.execute(loras.update().where(loras.c.base_model.is_(None)).values(base_model="SD1.5"))

    # 3. Add base_model column to embeddings table
    op.add_column(
        "embeddings",
        sa.Column("base_model", sa.String(50), nullable=True),
    )

    # 4. Set existing embeddings to SD1.5
    embeddings = sa.table(
        "embeddings",
        sa.column("base_model", sa.String),
    )
    op.execute(embeddings.update().where(embeddings.c.base_model.is_(None)).values(base_model="SD1.5"))


def downgrade() -> None:
    # Remove base_model from embeddings
    op.drop_column("embeddings", "base_model")

    # Revert LoRA base_model to null
    loras = sa.table(
        "loras",
        sa.column("base_model", sa.String),
    )
    op.execute(loras.update().values(base_model=None))

    # Revert LoRA lora_type changes
    # chibi-laugh was originally "pose"; J_huiben and ghibli_style_offset had
    # no lora_type set (NULL) — they were misclassified via calibration.
    loras_full = sa.table(
        "loras",
        sa.column("name", sa.String),
        sa.column("lora_type", sa.String),
    )
    op.execute(loras_full.update().where(loras_full.c.name == "chibi-laugh").values(lora_type="pose"))
    op.execute(loras_full.update().where(loras_full.c.name == "J_huiben").values(lora_type=None))
    op.execute(loras_full.update().where(loras_full.c.name == "ghibli_style_offset").values(lora_type=None))
