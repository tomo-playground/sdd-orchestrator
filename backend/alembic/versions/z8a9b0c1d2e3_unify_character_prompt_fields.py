"""Unify character prompt fields: 5 fields → positive_prompt + negative_prompt

Revision ID: z8a9b0c1d2e3
Revises: y7z8a9b0c1d2
Create Date: 2026-03-07

Merges:
  scene_positive_prompt + reference_positive_prompt → positive_prompt
  scene_negative_prompt + reference_negative_prompt + common_negative_prompts → negative_prompt
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "z8a9b0c1d2e3"
down_revision = "7d60fb618f36"
branch_labels = None
depends_on = None


def _merge_prompts(*prompts: str | None) -> str | None:
    """Merge multiple prompt strings with deduplication."""
    tokens: list[str] = []
    seen: set[str] = set()
    for prompt in prompts:
        if not prompt:
            continue
        for tok in prompt.split(","):
            t = tok.strip()
            norm = t.lower().replace(" ", "_")
            if t and norm not in seen:
                seen.add(norm)
                tokens.append(t)
    return ", ".join(tokens) if tokens else None


def upgrade() -> None:
    # 1. Add new unified columns
    op.add_column("characters", sa.Column("positive_prompt", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("negative_prompt", sa.Text(), nullable=True))

    # 2. Data migration: merge old fields into new
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, scene_positive_prompt, reference_positive_prompt, "
            "scene_negative_prompt, reference_negative_prompt, common_negative_prompts "
            "FROM characters"
        )
    ).fetchall()

    for row in rows:
        (
            char_id,
            scene_pos,
            ref_pos,
            scene_neg,
            ref_neg,
            common_neg,
        ) = row

        # Merge positive prompts
        new_positive = _merge_prompts(scene_pos, ref_pos)

        # Merge negative prompts (common_negative_prompts is ARRAY)
        common_neg_str = ", ".join(common_neg) if common_neg else None
        new_negative = _merge_prompts(scene_neg, ref_neg, common_neg_str)

        conn.execute(
            sa.text("UPDATE characters SET positive_prompt = :pos, negative_prompt = :neg WHERE id = :id"),
            {"pos": new_positive, "neg": new_negative, "id": char_id},
        )

    # 3. Drop old columns
    op.drop_column("characters", "scene_positive_prompt")
    op.drop_column("characters", "scene_negative_prompt")
    op.drop_column("characters", "reference_positive_prompt")
    op.drop_column("characters", "reference_negative_prompt")
    op.drop_column("characters", "common_negative_prompts")


def downgrade() -> None:
    # Restore old columns (data migration is NOT reversible — restores empty)
    op.add_column("characters", sa.Column("scene_positive_prompt", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("scene_negative_prompt", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("reference_positive_prompt", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("reference_negative_prompt", sa.Text(), nullable=True))
    op.add_column(
        "characters",
        sa.Column("common_negative_prompts", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.drop_column("characters", "positive_prompt")
    op.drop_column("characters", "negative_prompt")
