#!/usr/bin/env python3
"""[DEPRECATED] Migrate keywords.json v1 to PostgreSQL database.

NOTE: This script was used for one-time migration. keywords.json has been
removed and all keyword data is now managed in the PostgreSQL database.
Kept for historical reference only.

Original Usage:
    cd backend && uv run python scripts/migrate_keywords.py
"""

import json
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Synonym, Tag

# Category to DB mapping based on ROADMAP v2.0 spec
CATEGORY_MAPPING = {
    # Character tags
    "person": {"category": "character", "group_name": "subject", "priority": 2, "exclusive": False},
    "subject_count": {"category": "character", "group_name": "subject", "priority": 2, "exclusive": True},
    "gender": {"category": "character", "group_name": "identity", "priority": 3, "exclusive": False},
    "outfit": {"category": "character", "group_name": "clothing", "priority": 4, "exclusive": False},
    # Scene tags
    "action": {"category": "scene", "group_name": "pose", "priority": 5, "exclusive": False},
    "expression": {"category": "scene", "group_name": "pose", "priority": 5, "exclusive": False},
    "gaze": {"category": "scene", "group_name": "pose", "priority": 5, "exclusive": True},
    "shot_type": {"category": "scene", "group_name": "camera", "priority": 5, "exclusive": True},
    "camera_angle": {"category": "scene", "group_name": "camera", "priority": 5, "exclusive": True},
    "time": {"category": "scene", "group_name": "environment", "priority": 6, "exclusive": True},
    "weather": {"category": "scene", "group_name": "environment", "priority": 6, "exclusive": True},
    "location": {"category": "scene", "group_name": "environment", "priority": 6, "exclusive": False},
    "lighting": {"category": "scene", "group_name": "environment", "priority": 6, "exclusive": False},
    "mood": {"category": "scene", "group_name": "mood", "priority": 6, "exclusive": False},
    # Meta tags
    "quality": {"category": "meta", "group_name": "quality", "priority": 1, "exclusive": False},
    "style": {"category": "meta", "group_name": "style", "priority": 7, "exclusive": False},
    # Other (treated as character for now)
    "creature": {"category": "character", "group_name": "subject", "priority": 2, "exclusive": False},
    "object": {"category": "character", "group_name": "subject", "priority": 2, "exclusive": False},
}


def load_keywords_json() -> dict:
    """Load keywords.json file."""
    keywords_path = Path(__file__).parent.parent / "keywords.json"
    with open(keywords_path, encoding="utf-8") as f:
        return json.load(f)


def migrate_tags(db: Session, data: dict) -> dict[str, Tag]:
    """Migrate categories to tags table. Returns name -> Tag mapping."""
    tag_map: dict[str, Tag] = {}

    for category_name, tags in data.get("categories", {}).items():
        mapping = CATEGORY_MAPPING.get(category_name)
        if not mapping:
            print(f"  ⚠️  Unknown category: {category_name}, skipping...")
            continue

        for tag_name in tags:
            if tag_name in tag_map:
                continue  # Skip duplicates

            tag = Tag(
                name=tag_name,
                category=mapping["category"],
                group_name=mapping["group_name"],
                priority=mapping["priority"],
                exclusive=mapping["exclusive"],
            )
            db.add(tag)
            tag_map[tag_name] = tag

    db.flush()  # Get IDs
    return tag_map


def migrate_synonyms(db: Session, data: dict, tag_map: dict[str, Tag]) -> int:
    """Migrate synonyms to synonyms table. Returns count."""
    count = 0

    for tag_name, synonym_list in data.get("synonyms", {}).items():
        tag = tag_map.get(tag_name)
        if not tag:
            print(f"  ⚠️  Tag not found for synonym: {tag_name}")
            continue

        for synonym_name in synonym_list:
            synonym = Synonym(tag_id=tag.id, synonym=synonym_name)
            db.add(synonym)
            count += 1

    return count


def main():
    """Main migration function."""
    print("🚀 Starting keywords.json migration...")

    # Load data
    data = load_keywords_json()
    print(f"  📂 Loaded {len(data.get('categories', {}))} categories")

    # Migrate
    db = SessionLocal()
    try:
        # Check if already migrated
        existing_count = db.query(Tag).count()
        if existing_count > 0:
            print(f"  ⚠️  Database already has {existing_count} tags. Skipping migration.")
            print("  💡 To re-migrate, truncate tags and synonyms tables first.")
            return

        # Migrate tags
        tag_map = migrate_tags(db, data)
        print(f"  ✅ Migrated {len(tag_map)} tags")

        # Migrate synonyms
        synonym_count = migrate_synonyms(db, data, tag_map)
        print(f"  ✅ Migrated {synonym_count} synonyms")

        # Commit
        db.commit()
        print("🎉 Migration completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
