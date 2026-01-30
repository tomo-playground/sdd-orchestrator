"""add_tag_filters_table

Revision ID: 301bc8eb327e
Revises: 680342bf43a5
Create Date: 2026-01-29 12:31:23.712416

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '301bc8eb327e'
down_revision: str | Sequence[str] | None = '680342bf43a5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tag_filters table and populate with hardcoded ignore/skip tags."""
    # Create table
    op.create_table(
        'tag_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tag_name', sa.String(100), nullable=False),
        sa.Column('filter_type', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(200), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag_name')
    )
    op.create_index('ix_tag_filters_tag_name', 'tag_filters', ['tag_name'])

    # Populate with IGNORE_TOKENS from core.py
    connection = op.get_bind()

    ignore_tokens = [
        ("nsfw", "Sensitive content"),
        ("nude", "Sensitive content"),
        ("uncensored", "Sensitive content"),
        ("cleavage", "Sensitive content"),
        ("text", "Meta tag"),
        ("watermark", "Meta tag"),
        ("signature", "Meta tag"),
        ("logo", "Meta tag"),
        ("username", "Meta tag"),
        ("artist_name", "Meta tag"),
        ("copyright", "Meta tag"),
        ("low_quality", "Quality tag"),
        ("worst_quality", "Quality tag"),
        ("normal_quality", "Quality tag"),
        ("bad_quality", "Quality tag"),
        ("bad_anatomy", "Negative tag"),
        ("bad_hands", "Negative tag"),
        ("missing_fingers", "Negative tag"),
        ("extra_digits", "Negative tag"),
        ("fewer_digits", "Negative tag"),
        ("extra_limbs", "Negative tag"),
        ("cloned_face", "Negative tag"),
        ("mutated", "Negative tag"),
        ("deformed", "Negative tag"),
        ("disfigured", "Negative tag"),
        ("ugly", "Negative tag"),
        ("blur", "Negative tag"),
        ("blurry", "Negative tag"),
        ("jpeg_artifacts", "Negative tag"),
        ("cropped", "Meta tag"),
        ("out_of_frame", "Meta tag"),
        ("highres", "Meta tag"),
        ("absurdres", "Meta tag"),
    ]

    for tag, reason in ignore_tokens:
        connection.execute(
            sa.text("""
                INSERT INTO tag_filters (tag_name, filter_type, reason, active)
                VALUES (:tag, 'ignore', :reason, true)
            """),
            {"tag": tag, "reason": reason}
        )

    # Populate with SKIP_TAGS from core.py
    skip_tags = [
        # Anatomy
        ("breasts", "Anatomy"),
        ("large_breasts", "Anatomy"),
        ("medium_breasts", "Anatomy"),
        ("small_breasts", "Anatomy"),
        ("huge_breasts", "Anatomy"),
        ("collarbone", "Anatomy"),
        ("thighs", "Anatomy"),
        ("thick_thighs", "Anatomy"),
        ("navel", "Anatomy"),
        ("midriff", "Anatomy"),
        ("cleavage", "Anatomy"),
        ("ass", "Anatomy"),
        ("sideboob", "Anatomy"),
        ("underboob", "Anatomy"),
        ("nipples", "Anatomy"),
        ("areolae", "Anatomy"),
        ("crotch", "Anatomy"),
        ("groin", "Anatomy"),
        ("armpits", "Anatomy"),
        ("bare_shoulders", "Anatomy"),
        # Meta tags
        ("female_focus", "Meta tag"),
        ("solo_focus", "Meta tag"),
        ("no_humans", "Meta tag"),
        ("virtual_youtuber", "Meta tag"),
        ("vtuber", "Meta tag"),
        ("commentary", "Meta tag"),
        ("translation", "Meta tag"),
        ("border", "Meta tag"),
        ("letterboxed", "Meta tag"),
        ("pillarboxed", "Meta tag"),
        ("gradient", "Meta tag"),
        ("scan", "Meta tag"),
        ("screencap", "Meta tag"),
        ("official_art", "Meta tag"),
        # Sensitive subjects
        ("child", "Sensitive"),
        ("male_child", "Sensitive"),
        ("female_child", "Sensitive"),
        ("young", "Sensitive"),
        ("loli", "Sensitive"),
        ("shota", "Sensitive"),
        ("aged_down", "Sensitive"),
        ("aged_up", "Sensitive"),
        # Character-specific names
        ("watson_amelia", "Character name"),
        ("hatsune_miku", "Character name"),
        # Copyright tags
        ("vocaloid", "Copyright"),
        ("fate", "Copyright"),
        ("genshin_impact", "Copyright"),
        ("blue_archive", "Copyright"),
        # Too vague or redundant
        ("girl", "Too vague"),
        ("boy", "Too vague"),
        ("woman", "Too vague"),
        ("man", "Too vague"),
        ("female", "Too vague"),
        ("male", "Too vague"),
        ("anime", "Too vague"),
        ("manga", "Too vague"),
        ("illustration", "Too vague"),
    ]

    for tag, reason in skip_tags:
        connection.execute(
            sa.text("""
                INSERT INTO tag_filters (tag_name, filter_type, reason, active)
                VALUES (:tag, 'skip', :reason, true)
                ON CONFLICT (tag_name) DO NOTHING
            """),
            {"tag": tag, "reason": reason}
        )


def downgrade() -> None:
    """Remove tag_filters table."""
    op.drop_index('ix_tag_filters_tag_name', 'tag_filters')
    op.drop_table('tag_filters')
