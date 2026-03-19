import logging
import os
import sys

from sqlalchemy import text

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal
from models.media_asset import MediaAsset
from services.storage import initialize_storage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_garbage")


def cleanup_garbage():
    """
    Garbage Collection for MediaAssets.
    Deletes assets that are:
    1. 'Orphaned' in Generic Relation (owner_type set but owner missing) -> Not applicable yet as we have NULLs
    2. 'Unclaimed' (owner_type IS NULL) AND Not referenced by any Master table (Character, Project, etc.)
    3. 'Expired Temp' (is_temp=True) - (Optional for now)
    """
    db = SessionLocal()
    storage = initialize_storage()

    try:
        logger.info("🧹 Starting Garbage Collection...")

        # 1. Collect Asset IDs that are IN USE by Master Tables
        # Even if owner_type is NULL (legacy/migrated), if a Character points to it, we keep it.

        logger.info("🔍 Scanning references in Master tables...")

        # Queries to get used asset IDs
        queries = [
            "SELECT preview_image_asset_id FROM characters WHERE preview_image_asset_id IS NOT NULL",
            "SELECT preview_image_asset_id FROM loras WHERE preview_image_asset_id IS NOT NULL",
            "SELECT preview_image_asset_id FROM sd_models WHERE preview_image_asset_id IS NOT NULL",
            # Add any other tables that reference media_assets directly if any
        ]

        used_ids = set()
        for q in queries:
            rows = db.execute(text(q)).fetchall()
            for r in rows:
                used_ids.add(r[0])

        logger.info(f"🛡️  Found {len(used_ids)} assets referenced by Settings (Projects, Characters, etc.) - PROTECTED")

        # 2. Find Candidates for Deletion
        # Candidates: owner_type IS NULL AND id NOT IN used_ids
        # (Since we just migrated and didn't backfill owner_type, valid assets have owner_type=NULL too,
        # but they are in used_ids. The ones NOT in used_ids are the leftovers/garbage.)

        candidates_query = db.query(MediaAsset).filter(MediaAsset.owner_type.is_(None))

        all_null_owner_assets = candidates_query.all()
        logger.info(f"🔎 Found {len(all_null_owner_assets)} assets with NULL owner_type.")

        garbage_assets = []
        for asset in all_null_owner_assets:
            if asset.id not in used_ids:
                garbage_assets.append(asset)

        logger.info(f"🗑️  Identified {len(garbage_assets)} garbage assets to delete.")

        if not garbage_assets:
            logger.info("✨ No garbage found. System is clean.")
            return

        # 3. Validation (Double check against screenshot patterns if needed)
        # The user showed '/outputs/images/stored/scene_...'
        # Most garbage should look like that.

        # 4. Delete
        confirm = input(f"⚠️  About to DELETE {len(garbage_assets)} assets. Proceed? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("❌ Aborted.")
            return

        deleted_count = 0
        for asset in garbage_assets:
            try:
                # Delete from Storage
                if asset.storage_key and storage.exists(asset.storage_key):
                    storage.delete(asset.storage_key)
                    logger.info(f"   [Deleted File] {asset.storage_key}")
                else:
                    logger.warning(f"   [File Not Found] {asset.storage_key}")

                # Delete from DB
                db.delete(asset)
                deleted_count += 1
            except Exception as e:
                logger.error(f"   ❌ Failed to delete asset {asset.id}: {e}")

        db.commit()
        logger.info(f"✨ Cleanup Complete. Deleted {deleted_count} assets.")

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_garbage()
