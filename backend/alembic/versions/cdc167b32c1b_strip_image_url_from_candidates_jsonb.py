"""strip_image_url_from_candidates_jsonb

Remove "image_url" keys from scenes.candidates JSONB entries.
These are response-only fields that should never be persisted.

Revision ID: cdc167b32c1b
Revises: 746fbdbee6ea
Create Date: 2026-02-08 21:41:52.516356

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cdc167b32c1b'
down_revision: Union[str, Sequence[str], None] = '746fbdbee6ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Strip image_url from each element in scenes.candidates JSONB array."""
    # For each scene row with candidates, rebuild the JSONB array
    # removing the "image_url" key from every element.
    op.execute("""
        UPDATE scenes
        SET candidates = (
            SELECT jsonb_agg(elem - 'image_url')
            FROM jsonb_array_elements(candidates) AS elem
        )
        WHERE candidates IS NOT NULL
          AND candidates::text LIKE '%image_url%'
    """)


def downgrade() -> None:
    """No-op: removed data cannot be restored (it was always null/transient)."""
    pass
