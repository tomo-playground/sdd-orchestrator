"""Add expression/lighting conflict rules for cross-layer defense

Revision ID: q4j5k6l7m8n9
Revises: p3i4j5k6l7m8
Create Date: 2026-02-24 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "q4j5k6l7m8n9"
down_revision = "p3i4j5k6l7m8"
branch_labels = None
depends_on = None

# Conflict rules: (tag_a, tag_b) — bidirectional
CONFLICT_PAIRS = [
    ("gentle_smile", "crying"),
    ("gentle_smile", "sad"),
    ("gentle_smile", "angry"),
    ("gentle_smile", "frown"),
    ("soft_lighting", "dark"),
    ("soft_lighting", "dimly_lit"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Check if tag_rules table exists
    inspector = sa.inspect(conn)
    if "tag_rules" not in inspector.get_table_names():
        return

    tag_rules = sa.table(
        "tag_rules",
        sa.column("tag_a", sa.String),
        sa.column("tag_b", sa.String),
        sa.column("rule_type", sa.String),
        sa.column("description", sa.String),
    )

    for tag_a, tag_b in CONFLICT_PAIRS:
        # Check if rule already exists (either direction)
        existing = conn.execute(
            sa.select(sa.literal(1)).select_from(tag_rules).where(
                sa.or_(
                    sa.and_(tag_rules.c.tag_a == tag_a, tag_rules.c.tag_b == tag_b),
                    sa.and_(tag_rules.c.tag_a == tag_b, tag_rules.c.tag_b == tag_a),
                )
            )
        ).first()

        if not existing:
            op.execute(
                tag_rules.insert().values(
                    tag_a=tag_a,
                    tag_b=tag_b,
                    rule_type="conflict",
                    description=f"Cross-layer conflict: {tag_a} vs {tag_b}",
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "tag_rules" not in inspector.get_table_names():
        return

    tag_rules = sa.table(
        "tag_rules",
        sa.column("tag_a", sa.String),
        sa.column("tag_b", sa.String),
    )

    for tag_a, tag_b in CONFLICT_PAIRS:
        conn.execute(
            tag_rules.delete().where(
                sa.or_(
                    sa.and_(tag_rules.c.tag_a == tag_a, tag_rules.c.tag_b == tag_b),
                    sa.and_(tag_rules.c.tag_a == tag_b, tag_rules.c.tag_b == tag_a),
                )
            )
        )
