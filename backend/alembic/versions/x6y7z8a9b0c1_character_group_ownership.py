"""Character-Group ownership: move style_profile_id → group_id.

Revision ID: x6y7z8a9b0c1
Revises: w5x6y7z8a9b0
Create Date: 2026-03-02

Step A: Add group_id nullable + data migration
Step B: Set NOT NULL + drop style_profile_id
"""

import sqlalchemy as sa

from alembic import op

revision = "x6y7z8a9b0c1"
down_revision = "06678a84288b"
branch_labels = None
depends_on = None

# Data mapping: character style_profile_id → group_id
# Derived from current DB state (all 13 characters mapped)
CHARACTER_GROUP_MAPPING = {
    # 1분상식 (group 3, Flat Color style_profile 3)
    # 예민이, 유카리, 건우, 미도리, 하루
    3: [1, 19, 2, 3, 4],
    # 잠자리동화 (group 8, Children style_profile 4)
    # 수빈, 지호
    8: [5, 6],
    # 실화탐구 (group 9, Realistic style_profile 2)
    # 유나, 도윤
    9: [7, 8],
    # 꿈꾸는모험 (group 10, Ghibli style_profile 5)
    # 시온, 수아
    10: [9, 10],
    # 감성한스푼 (group 12, Shinkai style_profile 7)
    # 소라, 하나
    12: [11, 12],
}


def upgrade() -> None:
    # Step A: Add group_id as nullable first
    op.add_column("characters", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_characters_group_id",
        "characters",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_characters_group_id", "characters", ["group_id"])

    # Data migration: assign group_id based on known mapping
    conn = op.get_bind()
    for group_id, character_ids in CHARACTER_GROUP_MAPPING.items():
        for char_id in character_ids:
            conn.execute(
                sa.text("UPDATE characters SET group_id = :gid WHERE id = :cid"),
                {"gid": group_id, "cid": char_id},
            )

    # Catch any unmapped characters: assign based on style_profile_id → group mapping
    # style_profile_id 3 → group 3, 4 → 8, 2 → 9, 5 → 10, 7 → 12
    style_to_group = {3: 3, 4: 8, 2: 9, 5: 10, 7: 12}
    for style_id, group_id in style_to_group.items():
        conn.execute(
            sa.text("UPDATE characters SET group_id = :gid WHERE group_id IS NULL AND style_profile_id = :sid"),
            {"gid": group_id, "sid": style_id},
        )

    # Safety check: abort if any character still has no group_id (e.g., style_profile_id was NULL)
    orphans = conn.execute(sa.text("SELECT id, name FROM characters WHERE group_id IS NULL")).fetchall()
    if orphans:
        raise RuntimeError(
            f"Migration abort: {len(orphans)} character(s) have no group_id mapping: "
            f"{[(r[0], r[1]) for r in orphans]}. "
            "Manually assign them to a group before re-running."
        )

    # Step B: Set NOT NULL + drop style_profile_id
    op.alter_column("characters", "group_id", nullable=False)

    # Drop old style_profile FK + index + column
    op.drop_constraint("fk_characters_style_profile_id", "characters", type_="foreignkey")
    op.drop_index("ix_characters_style_profile_id", table_name="characters")
    op.drop_column("characters", "style_profile_id")


def downgrade() -> None:
    # Re-add style_profile_id
    op.add_column("characters", sa.Column("style_profile_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_characters_style_profile_id",
        "characters",
        "style_profiles",
        ["style_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_characters_style_profile_id", "characters", ["style_profile_id"])

    # Reverse data migration: group_id → style_profile_id via groups.style_profile_id
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE characters c SET style_profile_id = g.style_profile_id FROM groups g WHERE c.group_id = g.id")
    )

    # Drop group_id
    op.drop_index("ix_characters_group_id", table_name="characters")
    op.drop_constraint("fk_characters_group_id", "characters", type_="foreignkey")
    op.drop_column("characters", "group_id")
