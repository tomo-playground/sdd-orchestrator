"""migrate candidates to media_asset_ids

Convert scenes.candidates from URL-based format to media_asset_id format.

Before: [{"image_url": "http://localhost:9000/shorts-producer/projects/..."}]
After:  [{"media_asset_id": 1234, "match_rate": null}]

Revision ID: 209d7efeec5f
Revises: z0a1b2c3d4e5
Create Date: 2026-02-06

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "209d7efeec5f"
down_revision: str | Sequence[str] | None = "z0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert candidates from URL format to media_asset_id format."""
    # Log records that will be migrated
    op.execute("""
        DO $$
        DECLARE
            total_count INTEGER;
            matched_count INTEGER;
            unmatched_count INTEGER;
        BEGIN
            -- Count total candidate entries
            SELECT COUNT(*) INTO total_count
            FROM scenes s,
            jsonb_array_elements(s.candidates) as elem
            WHERE s.candidates IS NOT NULL
              AND s.candidates::text != 'null'
              AND s.candidates::text != '[]';

            -- Count matched entries
            WITH candidate_urls AS (
                SELECT
                    REGEXP_REPLACE(
                        elem->>'image_url',
                        '^https?://[^/]+/shorts-producer/',
                        ''
                    ) as extracted_key
                FROM scenes s,
                jsonb_array_elements(s.candidates) as elem
                WHERE s.candidates IS NOT NULL
                  AND s.candidates::text != 'null'
                  AND s.candidates::text != '[]'
            )
            SELECT COUNT(*) INTO matched_count
            FROM candidate_urls cu
            JOIN media_assets ma ON ma.storage_key = cu.extracted_key;

            unmatched_count := total_count - matched_count;

            RAISE NOTICE 'Candidates migration: % total, % matched, % unmatched',
                total_count, matched_count, unmatched_count;

            IF unmatched_count > 0 THEN
                RAISE WARNING 'Some candidates could not be matched to media_assets!';
            END IF;
        END $$;
    """)

    # Perform the actual migration
    # For each scene with candidates, rebuild the JSONB array with media_asset_ids
    op.execute("""
        UPDATE scenes s
        SET candidates = (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'media_asset_id', ma.id,
                    'match_rate', NULL
                )
            )
            FROM jsonb_array_elements(s.candidates) as elem
            LEFT JOIN media_assets ma ON ma.storage_key = REGEXP_REPLACE(
                elem->>'image_url',
                '^https?://[^/]+/shorts-producer/',
                ''
            )
            WHERE ma.id IS NOT NULL
        )
        WHERE s.candidates IS NOT NULL
          AND s.candidates::text != 'null'
          AND s.candidates::text != '[]'
          AND EXISTS (
              SELECT 1 FROM jsonb_array_elements(s.candidates) as elem
              WHERE elem->>'image_url' IS NOT NULL
          );
    """)


def downgrade() -> None:
    """Revert candidates from media_asset_id format back to URL format.

    Uses STORAGE_PUBLIC_URL pattern: http://localhost:9000/shorts-producer/{storage_key}
    """
    op.execute("""
        UPDATE scenes s
        SET candidates = (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'image_url',
                    'http://localhost:9000/shorts-producer/' || ma.storage_key
                )
            )
            FROM jsonb_array_elements(s.candidates) as elem
            LEFT JOIN media_assets ma ON ma.id = (elem->>'media_asset_id')::INTEGER
            WHERE ma.id IS NOT NULL
        )
        WHERE s.candidates IS NOT NULL
          AND s.candidates::text != 'null'
          AND s.candidates::text != '[]'
          AND EXISTS (
              SELECT 1 FROM jsonb_array_elements(s.candidates) as elem
              WHERE elem->>'media_asset_id' IS NOT NULL
          );
    """)
