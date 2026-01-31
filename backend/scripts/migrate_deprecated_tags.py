#!/usr/bin/env python3
"""Migrate deprecated tags in existing data to their active replacements.

This script:
1. Finds all deprecated tags with replacements
2. Updates scene_tags, character_tags associations
3. Updates prompt_histories
4. Logs all changes for audit trail

Usage:
    python scripts/migrate_deprecated_tags.py [--dry-run] [--verbose]
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Tag
from models.associations import CharacterTag, SceneTag


def get_deprecated_tags_map(db) -> dict[int, int]:
    """Get mapping of deprecated tag IDs to replacement tag IDs.

    Returns:
        {deprecated_tag_id: replacement_tag_id}
    """
    deprecated = db.query(Tag).filter(
        Tag.is_active.is_(False),
        Tag.replacement_tag_id.isnot(None)
    ).all()

    return {tag.id: tag.replacement_tag_id for tag in deprecated}


def migrate_scene_tags(db, replacement_map: dict[int, int], dry_run: bool = False, verbose: bool = False):
    """Migrate deprecated tags in scene_tags table."""
    print("\n=== Migrating scene_tags ===")

    affected = db.query(SceneTag).filter(SceneTag.tag_id.in_(replacement_map.keys())).all()

    if not affected:
        print("No deprecated tags found in scene_tags")
        return 0

    changes = []
    for scene_tag in affected:
        old_tag = db.query(Tag).filter(Tag.id == scene_tag.tag_id).first()
        new_tag = db.query(Tag).filter(Tag.id == replacement_map[scene_tag.tag_id]).first()

        changes.append({
            "scene_id": scene_tag.scene_id,
            "old_tag": old_tag.name if old_tag else "Unknown",
            "new_tag": new_tag.name if new_tag else "Unknown"
        })

        if verbose or dry_run:
            print(f"  Scene {scene_tag.scene_id}: {old_tag.name} → {new_tag.name}")

        if not dry_run:
            scene_tag.tag_id = replacement_map[scene_tag.tag_id]

    if not dry_run:
        db.commit()
        print(f"✓ Updated {len(changes)} scene_tag associations")
    else:
        print(f"[DRY RUN] Would update {len(changes)} scene_tag associations")

    return len(changes)


def migrate_character_tags(db, replacement_map: dict[int, int], dry_run: bool = False, verbose: bool = False):
    """Migrate deprecated tags in character_tags table."""
    print("\n=== Migrating character_tags ===")

    affected = db.query(CharacterTag).filter(CharacterTag.tag_id.in_(replacement_map.keys())).all()

    if not affected:
        print("No deprecated tags found in character_tags")
        return 0

    changes = []
    for char_tag in affected:
        old_tag = db.query(Tag).filter(Tag.id == char_tag.tag_id).first()
        new_tag = db.query(Tag).filter(Tag.id == replacement_map[char_tag.tag_id]).first()

        changes.append({
            "character_id": char_tag.character_id,
            "old_tag": old_tag.name if old_tag else "Unknown",
            "new_tag": new_tag.name if new_tag else "Unknown"
        })

        if verbose or dry_run:
            print(f"  Character {char_tag.character_id}: {old_tag.name} → {new_tag.name}")

        if not dry_run:
            char_tag.tag_id = replacement_map[char_tag.tag_id]

    if not dry_run:
        db.commit()
        print(f"✓ Updated {len(changes)} character_tag associations")
    else:
        print(f"[DRY RUN] Would update {len(changes)} character_tag associations")

    return len(changes)


def main():
    parser = argparse.ArgumentParser(description="Migrate deprecated tags to replacements")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    db = SessionLocal()

    try:
        print("=" * 60)
        print("Tag Deprecation Migration Script")
        print("=" * 60)

        # Get replacement map
        replacement_map = get_deprecated_tags_map(db)

        if not replacement_map:
            print("\n✓ No deprecated tags with replacements found")
            return

        print(f"\nFound {len(replacement_map)} deprecated tags with replacements:")
        for old_id, new_id in replacement_map.items():
            old_tag = db.query(Tag).filter(Tag.id == old_id).first()
            new_tag = db.query(Tag).filter(Tag.id == new_id).first()
            print(f"  - {old_tag.name} → {new_tag.name}")

        # Migrate
        scene_count = migrate_scene_tags(db, replacement_map, args.dry_run, args.verbose)
        char_count = migrate_character_tags(db, replacement_map, args.dry_run, args.verbose)

        # Summary
        print("\n" + "=" * 60)
        if args.dry_run:
            print("DRY RUN SUMMARY (no changes applied)")
        else:
            print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Scene tags updated: {scene_count}")
        print(f"Character tags updated: {char_count}")
        print(f"Total: {scene_count + char_count}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
