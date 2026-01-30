#!/usr/bin/env python3
"""Migrate reference image filenames to ID-based format (ID_Name.png).

This script renames existing reference images from name-based format (e.g., "Doremi.png")
to ID-based format (e.g., "9_Doremi.png") by looking up character IDs in the database.

Usage:
    python scripts/migrate_reference_filenames.py [--dry-run]

Options:
    --dry-run: Show what would be renamed without actually renaming files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import ASSETS_DIR, logger
from database import SessionLocal
from models import Character

REFERENCE_DIR = ASSETS_DIR / "references"


def migrate_reference_filenames(dry_run: bool = False) -> None:
    """Migrate reference image filenames to ID_Name.png format.

    Args:
        dry_run: If True, only show what would be renamed without actually renaming
    """
    if not REFERENCE_DIR.exists():
        logger.error(f"Reference directory not found: {REFERENCE_DIR}")
        return

    db = SessionLocal()
    try:
        # Build character lookup map (name -> Character)
        chars = db.query(Character).all()
        char_map = {char.name.lower(): char for char in chars}

        renamed_count = 0
        skipped_count = 0
        not_found_count = 0

        logger.info("Starting reference image filename migration...")
        logger.info(f"Found {len(chars)} characters in database")

        for path in REFERENCE_DIR.glob("*.png"):
            stem = path.stem

            # Skip files already in ID_Name format
            if "_" in stem and stem.split("_", 1)[0].isdigit():
                logger.info(f"⏭️  Skip (already ID-based): {path.name}")
                skipped_count += 1
                continue

            # Try to find character by name (case-insensitive)
            char = char_map.get(stem.lower())

            # Try partial matching if exact match fails
            if not char:
                stem_lower = stem.lower()
                for char_name_lower, candidate_char in char_map.items():
                    if stem_lower in char_name_lower or char_name_lower in stem_lower:
                        char = candidate_char
                        logger.info(f"   Partial match: '{stem}' → '{char.name}' (ID: {char.id})")
                        break

            if not char:
                logger.warning(f"❌ Character not found in DB: {path.name}")
                not_found_count += 1
                continue

            # Generate new filename: ID_Name.png
            # Use original filename stem as display name (not DB name)
            new_filename = f"{char.id}_{stem}.png"
            new_path = REFERENCE_DIR / new_filename

            if new_path.exists():
                logger.warning(f"⚠️  Target already exists: {new_filename}")
                skipped_count += 1
                continue

            if dry_run:
                logger.info(f"[DRY RUN] {path.name} → {new_filename} (ID: {char.id})")
            else:
                path.rename(new_path)
                logger.info(f"✅ Renamed: {path.name} → {new_filename} (ID: {char.id})")

            renamed_count += 1

        logger.info("\nMigration Summary:")
        logger.info(f"  ✅ Renamed: {renamed_count}")
        logger.info(f"  ⏭️  Skipped: {skipped_count}")
        logger.info(f"  ❌ Not found: {not_found_count}")

        if dry_run:
            logger.info("\n[DRY RUN] No files were actually renamed. Run without --dry-run to apply changes.")

    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate reference image filenames to ID-based format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without actually renaming files",
    )
    args = parser.parse_args()

    migrate_reference_filenames(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
