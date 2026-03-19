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

# Conflict rules: (source_tag_name, target_tag_name) — each inserted as one row
# TagRuleCache builds bidirectional lookup at runtime.
CONFLICT_PAIRS = [
    ("gentle_smile", "crying"),
    ("gentle_smile", "sad"),
    ("gentle_smile", "angry"),
    ("gentle_smile", "frown"),
    ("soft_lighting", "dark"),
]


def upgrade() -> None:
    conn = op.get_bind()

    inspector = sa.inspect(conn)
    if "tag_rules" not in inspector.get_table_names():
        return
    if "tags" not in inspector.get_table_names():
        return

    tags = sa.table("tags", sa.column("id", sa.Integer), sa.column("name", sa.String))
    tag_rules = sa.table(
        "tag_rules",
        sa.column("source_tag_id", sa.Integer),
        sa.column("target_tag_id", sa.Integer),
        sa.column("rule_type", sa.String),
        sa.column("message", sa.String),
        sa.column("priority", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )

    # Build name→id map
    rows = conn.execute(sa.select(tags.c.id, tags.c.name)).fetchall()
    name_to_id = {r[1]: r[0] for r in rows}

    for src_name, tgt_name in CONFLICT_PAIRS:
        src_id = name_to_id.get(src_name)
        tgt_id = name_to_id.get(tgt_name)
        if not src_id or not tgt_id:
            continue

        # Check if rule already exists (either direction)
        existing = conn.execute(
            sa.select(sa.literal(1))
            .select_from(tag_rules)
            .where(
                sa.or_(
                    sa.and_(tag_rules.c.source_tag_id == src_id, tag_rules.c.target_tag_id == tgt_id),
                    sa.and_(tag_rules.c.source_tag_id == tgt_id, tag_rules.c.target_tag_id == src_id),
                )
            )
        ).first()

        if not existing:
            op.execute(
                tag_rules.insert().values(
                    source_tag_id=src_id,
                    target_tag_id=tgt_id,
                    rule_type="conflict",
                    message=f"Cross-layer conflict: {src_name} vs {tgt_name}",
                    priority=0,
                    is_active=True,
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "tag_rules" not in inspector.get_table_names():
        return
    if "tags" not in inspector.get_table_names():
        return

    tags = sa.table("tags", sa.column("id", sa.Integer), sa.column("name", sa.String))
    tag_rules = sa.table(
        "tag_rules",
        sa.column("source_tag_id", sa.Integer),
        sa.column("target_tag_id", sa.Integer),
    )

    rows = conn.execute(sa.select(tags.c.id, tags.c.name)).fetchall()
    name_to_id = {r[1]: r[0] for r in rows}

    for src_name, tgt_name in CONFLICT_PAIRS:
        src_id = name_to_id.get(src_name)
        tgt_id = name_to_id.get(tgt_name)
        if not src_id or not tgt_id:
            continue

        conn.execute(
            tag_rules.delete().where(
                sa.or_(
                    sa.and_(tag_rules.c.source_tag_id == src_id, tag_rules.c.target_tag_id == tgt_id),
                    sa.and_(tag_rules.c.source_tag_id == tgt_id, tag_rules.c.target_tag_id == src_id),
                )
            )
        )
