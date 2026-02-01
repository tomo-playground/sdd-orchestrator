"""normalize image storage key in logging tables

Revision ID: 2028041a8e51
Revises: 3befa9fd7c2e
Create Date: 2026-02-01 16:19:56.170308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2028041a8e51'
down_revision: Union[str, Sequence[str], None] = '3befa9fd7c2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Rename image_url → image_storage_key and normalize data."""
    # 1. Rename columns
    op.alter_column('activity_logs', 'image_url',
                    new_column_name='image_storage_key')
    op.alter_column('scene_quality_scores', 'image_url',
                    new_column_name='image_storage_key')

    # 2. Data cleanup: MinIO URL → Storage Key
    # Pattern: http://localhost:9000/shorts-producer/projects/... → projects/...
    op.execute("""
        UPDATE activity_logs
        SET image_storage_key = REGEXP_REPLACE(
            image_storage_key,
            '^https?://[^/]+/shorts-producer/',
            ''
        )
        WHERE image_storage_key ~ '^https?://';
    """)

    op.execute("""
        UPDATE scene_quality_scores
        SET image_storage_key = REGEXP_REPLACE(
            image_storage_key,
            '^https?://[^/]+/shorts-producer/',
            ''
        )
        WHERE image_storage_key ~ '^https?://';
    """)

    # 3. Null out irrecoverable paths (absolute filesystem paths)
    op.execute("""
        UPDATE activity_logs
        SET image_storage_key = NULL
        WHERE image_storage_key LIKE '/outputs/%';
    """)

    op.execute("""
        UPDATE scene_quality_scores
        SET image_storage_key = NULL
        WHERE image_storage_key LIKE '/outputs/%';
    """)


def downgrade() -> None:
    """Downgrade schema: Revert column names."""
    op.alter_column('activity_logs', 'image_storage_key',
                    new_column_name='image_url')
    op.alter_column('scene_quality_scores', 'image_storage_key',
                    new_column_name='image_url')
