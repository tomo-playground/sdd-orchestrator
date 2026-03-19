"""add enum check constraints

Revision ID: 3e30b3b1d7cc
Revises: 22e99aa5ecbd
Create Date: 2026-02-10

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3e30b3b1d7cc"
down_revision: str | Sequence[str] | None = "22e99aa5ecbd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Existing constraints to drop & recreate with expanded values
DROP_FIRST = [
    ("voice_presets", "ck_voice_presets_source_type"),
]

# (table, column, constraint_name, allowed_values)
CHECKS = [
    ("tag_rules", "rule_type", "ck_tag_rules_rule_type", ["conflict", "requires"]),
    ("tag_filters", "filter_type", "ck_tag_filters_filter_type", ["ignore", "skip", "restricted"]),
    (
        "classification_rules",
        "rule_type",
        "ck_classification_rules_rule_type",
        ["exact", "prefix", "suffix", "contains"],
    ),
    ("voice_presets", "source_type", "ck_voice_presets_source_type", ["generated", "uploaded"]),
    ("render_presets", "bgm_mode", "ck_render_presets_bgm_mode", ["file", "ai"]),
    ("embeddings", "embedding_type", "ck_embeddings_embedding_type", ["negative", "positive", "style"]),
    ("tags", "usage_scope", "ck_tags_usage_scope", ["PERMANENT", "TRANSIENT", "ANY"]),
    ("media_assets", "file_type", "ck_media_assets_file_type", ["image", "audio", "video"]),
]


def upgrade() -> None:
    """Add CHECK constraints to enum string columns."""
    # Drop existing narrow constraints first
    for table, name in DROP_FIRST:
        op.drop_constraint(name, table, type_="check")

    for table, column, name, values in CHECKS:
        values_sql = ", ".join(f"'{v}'" for v in values)
        op.create_check_constraint(name, table, f"{column} IN ({values_sql})")


def downgrade() -> None:
    """Remove CHECK constraints (restore original voice_presets constraint)."""
    for table, _column, name, _values in CHECKS:
        op.drop_constraint(name, table, type_="check")

    # Restore original narrow constraint
    op.create_check_constraint("ck_voice_presets_source_type", "voice_presets", "source_type = 'generated'")
