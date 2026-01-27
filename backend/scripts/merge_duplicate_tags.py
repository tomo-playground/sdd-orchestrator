#!/usr/bin/env python3
"""Merge duplicate tags: underscore format → space format.

Problem: Tags like "brown_hair" and "brown hair" both exist in DB.
- WD14 uses space format ("brown hair")
- SD uses underscore format ("brown_hair")

Solution:
- Keep space format in DB (for WD14 matching)
- Convert to underscore in compose_prompt_tokens() (for SD)

This script:
1. Find all duplicate tag pairs (space vs underscore)
2. Merge effectiveness data: underscore → space
3. Update foreign key references
4. Delete underscore duplicates
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models.tag import Tag, TagEffectiveness
from sqlalchemy import text


def find_duplicate_pairs(db):
    """Find all duplicate tag pairs (space vs underscore).

    Returns:
        List of tuples: (space_tag, underscore_tag, space_id, underscore_id)
    """
    # Get all tags
    all_tags = db.query(Tag.id, Tag.name).all()

    # Build space → underscore mapping
    space_map = {}  # "brown hair" → tag_id
    underscore_map = {}  # "brown_hair" → tag_id

    for tag_id, name in all_tags:
        if " " in name:
            space_map[name] = tag_id
        elif "_" in name:
            underscore_map[name] = tag_id

    # Find pairs
    pairs = []
    for space_name, space_id in space_map.items():
        underscore_name = space_name.replace(" ", "_")
        if underscore_name in underscore_map:
            underscore_id = underscore_map[underscore_name]
            pairs.append((space_name, underscore_name, space_id, underscore_id))

    return pairs


def merge_effectiveness(db, space_id: int, underscore_id: int):
    """Merge effectiveness data from underscore to space tag."""
    space_eff = db.query(TagEffectiveness).filter(
        TagEffectiveness.tag_id == space_id
    ).first()

    underscore_eff = db.query(TagEffectiveness).filter(
        TagEffectiveness.tag_id == underscore_id
    ).first()

    if not underscore_eff:
        return "no underscore data"

    if not space_eff:
        # Transfer ownership
        underscore_eff.tag_id = space_id
        return "transferred"

    # Merge data
    space_eff.use_count += underscore_eff.use_count
    space_eff.match_count += underscore_eff.match_count
    space_eff.total_confidence += underscore_eff.total_confidence

    # Recalculate effectiveness
    if space_eff.use_count > 0:
        space_eff.effectiveness = space_eff.match_count / space_eff.use_count

    # Delete underscore record
    db.delete(underscore_eff)

    return f"merged ({underscore_eff.use_count} uses)"


def update_foreign_keys(db, space_id: int, underscore_id: int):
    """Update foreign key references from underscore to space."""
    # synonyms.tag_id
    db.execute(
        text("UPDATE synonyms SET tag_id = :space WHERE tag_id = :underscore"),
        {"space": space_id, "underscore": underscore_id}
    )

    # tag_rules.source_tag_id
    db.execute(
        text("UPDATE tag_rules SET source_tag_id = :space WHERE source_tag_id = :underscore"),
        {"space": space_id, "underscore": underscore_id}
    )

    # tag_rules.target_tag_id
    db.execute(
        text("UPDATE tag_rules SET target_tag_id = :space WHERE target_tag_id = :underscore"),
        {"space": space_id, "underscore": underscore_id}
    )

    # Integer arrays in characters table
    # identity_tags, clothing_tags are integer[] arrays of tag IDs
    db.execute(
        text("""
            UPDATE characters
            SET identity_tags = array_replace(identity_tags, :underscore, :space)
            WHERE :underscore = ANY(identity_tags)
        """),
        {"space": space_id, "underscore": underscore_id}
    )

    db.execute(
        text("""
            UPDATE characters
            SET clothing_tags = array_replace(clothing_tags, :underscore, :space)
            WHERE :underscore = ANY(clothing_tags)
        """),
        {"space": space_id, "underscore": underscore_id}
    )


def main():
    db = SessionLocal()

    try:
        print("Finding duplicate tag pairs...")
        pairs = find_duplicate_pairs(db)
        print(f"Found {len(pairs)} duplicate pairs\n")

        if not pairs:
            print("No duplicates found. Exiting.")
            return

        # Show preview
        print("Preview (first 5):")
        for space_name, underscore_name, space_id, underscore_id in pairs[:5]:
            print(f"  '{space_name}' (ID {space_id}) ← '{underscore_name}' (ID {underscore_id})")
        print()

        # Auto-approve (running in non-interactive mode)
        print(f"Auto-merging all {len(pairs)} pairs...")
        print()
        for space_name, underscore_name, space_id, underscore_id in pairs:
            # Merge effectiveness
            eff_result = merge_effectiveness(db, space_id, underscore_id)

            # Update foreign keys
            update_foreign_keys(db, space_id, underscore_id)

            # Delete underscore tag
            underscore_tag = db.query(Tag).filter(Tag.id == underscore_id).first()
            if underscore_tag:
                db.delete(underscore_tag)

            print(f"✓ '{space_name}' ← '{underscore_name}' ({eff_result})")

        db.commit()
        print(f"\n✅ Successfully merged {len(pairs)} duplicate pairs")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
