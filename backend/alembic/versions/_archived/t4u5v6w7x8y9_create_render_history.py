"""create_render_history

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-02-04

Create render_history table and backfill from storyboards.recent_videos + video_asset_id.
"""

import sqlalchemy as sa

from alembic import op

revision = "t4u5v6w7x8y9"
down_revision = "s3t4u5v6w7x8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "render_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "storyboard_id",
            sa.Integer(),
            sa.ForeignKey("storyboards.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "media_asset_id",
            sa.Integer(),
            sa.ForeignKey("media_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("label", sa.String(20), nullable=False),
        sa.Column("video_url", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_render_history_sb_created",
        "render_history",
        ["storyboard_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # Backfill from recent_videos JSONB
    # ------------------------------------------------------------------
    conn = op.get_bind()

    rows = conn.execute(
        sa.text("""
            SELECT id, recent_videos, video_asset_id
            FROM storyboards
            WHERE recent_videos IS NOT NULL OR video_asset_id IS NOT NULL
        """)
    ).fetchall()

    seen: set[tuple[int, str]] = set()  # (storyboard_id, video_url) dedup

    for row in rows:
        sb_id = row[0]
        recent = row[1]  # JSONB list or None
        video_asset_id = row[2]

        # 1) Backfill from recent_videos entries
        if recent and isinstance(recent, list):
            for entry in recent:
                url = entry.get("url", "")
                label = entry.get("label", "full")
                created_ms = entry.get("createdAt", 0)
                if not url:
                    continue

                key = (sb_id, url)
                if key in seen:
                    continue
                seen.add(key)

                # Try to find matching media_asset by filename
                filename = url.rsplit("/", 1)[-1] if "/" in url else url
                asset_row = conn.execute(
                    sa.text("SELECT id FROM media_assets WHERE file_name = :fn AND file_type = 'video' LIMIT 1"),
                    {"fn": filename},
                ).fetchone()

                asset_id = asset_row[0] if asset_row else None

                # Use to_timestamp if ms available, otherwise now()
                if created_ms:
                    conn.execute(
                        sa.text("""
                            INSERT INTO render_history (storyboard_id, media_asset_id, label, video_url, created_at, updated_at)
                            VALUES (:sb, :asset, :label, :url, to_timestamp(:ms / 1000.0), now())
                        """),
                        {"sb": sb_id, "asset": asset_id, "label": label, "url": url, "ms": created_ms},
                    )
                else:
                    conn.execute(
                        sa.text("""
                            INSERT INTO render_history (storyboard_id, media_asset_id, label, video_url, created_at, updated_at)
                            VALUES (:sb, :asset, :label, :url, now(), now())
                        """),
                        {"sb": sb_id, "asset": asset_id, "label": label, "url": url},
                    )

        # 2) Backfill video_asset_id if not already covered
        if video_asset_id:
            asset_url_row = conn.execute(
                sa.text("SELECT storage_key, file_name FROM media_assets WHERE id = :aid"),
                {"aid": video_asset_id},
            ).fetchone()

            if asset_url_row:
                storage_key = asset_url_row[0]
                # Build a simple URL placeholder — the actual URL is resolved at runtime
                url_candidate = f"/assets/{storage_key}"

                key = (sb_id, url_candidate)
                # Check if this asset was already inserted via recent_videos
                already = conn.execute(
                    sa.text("SELECT 1 FROM render_history WHERE storyboard_id = :sb AND media_asset_id = :aid LIMIT 1"),
                    {"sb": sb_id, "aid": video_asset_id},
                ).fetchone()

                if not already:
                    conn.execute(
                        sa.text("""
                            INSERT INTO render_history (storyboard_id, media_asset_id, label, video_url, created_at, updated_at)
                            VALUES (:sb, :asset, 'full', :url, now(), now())
                        """),
                        {"sb": sb_id, "asset": video_asset_id, "url": url_candidate},
                    )


def downgrade() -> None:
    op.drop_index("ix_render_history_sb_created", table_name="render_history")
    op.drop_table("render_history")
