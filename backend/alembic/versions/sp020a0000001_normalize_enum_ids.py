"""Normalize structure/language enum IDs to snake_case/lowercase.

Revision ID: sp020a0000001
Revises: sp073a0000001
Create Date: 2026-03-24

SP-020: Title Case → snake_case (structure), Title Case → lowercase (language).
Data-only migration, no schema changes.

NOTE (Confession): 'Confession' rows are merged into 'monologue' in upgrade().
On downgrade, these rows become 'Monologue'. Original 'Confession' data is not
preserved — this is intentional (Confession was removed in sp056).

NOTE (voice_presets): lowercase normalization in upgrade() is reversed by
restoring standard Title Case values in downgrade(). Non-standard casing that
existed before upgrade will be normalized to Title Case on rollback.
"""

from alembic import op

revision = "sp020a0000001"
down_revision = "sp073a0000001"
branch_labels = None
depends_on = None


def upgrade():
    # Structure: Title Case → snake_case
    op.execute("UPDATE storyboards SET structure = 'monologue' WHERE structure = 'Monologue'")
    op.execute("UPDATE storyboards SET structure = 'dialogue' WHERE structure = 'Dialogue'")
    op.execute(
        "UPDATE storyboards SET structure = 'narrated_dialogue' "
        "WHERE structure IN ('Narrated Dialogue', 'Narrated_Dialogue')"
    )
    op.execute("UPDATE storyboards SET structure = 'monologue' WHERE structure = 'Confession'")

    # Language: Title Case → lowercase
    op.execute("UPDATE storyboards SET language = 'korean' WHERE language = 'Korean'")
    op.execute("UPDATE storyboards SET language = 'english' WHERE language = 'English'")
    op.execute("UPDATE storyboards SET language = 'japanese' WHERE language = 'Japanese'")

    # voice_presets: ensure lowercase
    op.execute("UPDATE voice_presets SET language = LOWER(language) WHERE language != LOWER(language)")


def downgrade():
    # Reversible: snake_case → Title Case
    # NOTE: 'Confession' rows were merged into 'monologue' in upgrade().
    # They will be restored as 'Monologue' here — original 'Confession' values are not recoverable.
    op.execute("UPDATE storyboards SET structure = 'Monologue' WHERE structure = 'monologue'")
    op.execute("UPDATE storyboards SET structure = 'Dialogue' WHERE structure = 'dialogue'")
    op.execute("UPDATE storyboards SET structure = 'Narrated Dialogue' WHERE structure = 'narrated_dialogue'")

    op.execute("UPDATE storyboards SET language = 'Korean' WHERE language = 'korean'")
    op.execute("UPDATE storyboards SET language = 'English' WHERE language = 'english'")
    op.execute("UPDATE storyboards SET language = 'Japanese' WHERE language = 'japanese'")

    # voice_presets: lowercase → Title Case (mirrors upgrade LOWER() normalization)
    op.execute("UPDATE voice_presets SET language = 'Korean' WHERE language = 'korean'")
    op.execute("UPDATE voice_presets SET language = 'English' WHERE language = 'english'")
    op.execute("UPDATE voice_presets SET language = 'Japanese' WHERE language = 'japanese'")
