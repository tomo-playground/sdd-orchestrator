"""Remove Clone mode: add voice_seed to voice_presets, drop voice_ref_audio_url from render_presets

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-02-03
"""
import sqlalchemy as sa

from alembic import op

revision = "h2i3j4k5l6m7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # 1. Add voice_seed column to voice_presets
    if not _column_exists("voice_presets", "voice_seed"):
        op.add_column(
            "voice_presets",
            sa.Column("voice_seed", sa.Integer(), nullable=True),
        )

    # 2. Backfill voice_seed from hash(voice_design_prompt) for existing presets
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE voice_presets "
            "SET voice_seed = abs(hashtext(voice_design_prompt)) % 2147483648 "
            "WHERE voice_design_prompt IS NOT NULL AND voice_seed IS NULL"
        )
    )

    # 3. Drop voice_ref_audio_url from render_presets
    if _column_exists("render_presets", "voice_ref_audio_url"):
        op.drop_column("render_presets", "voice_ref_audio_url")

    # 4. Drop project_id from voice_presets (global presets only)
    if _column_exists("voice_presets", "project_id"):
        # Drop dependent indexes/constraints first
        try:
            op.drop_index("uq_voice_presets_project_name", "voice_presets")
        except Exception:
            pass
        try:
            op.drop_index("ix_voice_presets_project_id", "voice_presets")
        except Exception:
            pass
        op.drop_column("voice_presets", "project_id")

    # 5. Update source_type check constraint (remove 'uploaded' option)
    try:
        op.drop_constraint("ck_voice_presets_source_type", "voice_presets", type_="check")
    except Exception:
        pass  # Constraint may not exist
    op.create_check_constraint(
        "ck_voice_presets_source_type",
        "voice_presets",
        "source_type IN ('generated')",
    )


def downgrade() -> None:
    # Restore source_type check constraint
    try:
        op.drop_constraint("ck_voice_presets_source_type", "voice_presets", type_="check")
    except Exception:
        pass
    op.create_check_constraint(
        "ck_voice_presets_source_type",
        "voice_presets",
        "source_type IN ('generated', 'uploaded')",
    )

    # Re-add project_id to voice_presets
    if not _column_exists("voice_presets", "project_id"):
        op.add_column(
            "voice_presets",
            sa.Column("project_id", sa.Integer(),
                      sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_voice_presets_project_id", "voice_presets", ["project_id"])
        op.create_index(
            "uq_voice_presets_project_name", "voice_presets",
            ["project_id", "name"], unique=True,
            postgresql_where=sa.text("project_id IS NOT NULL"),
        )

    # Re-add voice_ref_audio_url to render_presets
    op.add_column(
        "render_presets",
        sa.Column("voice_ref_audio_url", sa.Text(), nullable=True),
    )

    # Drop voice_seed from voice_presets
    op.drop_column("voice_presets", "voice_seed")
