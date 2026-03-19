#!/usr/bin/env python3
"""Revert DB tags to underscore format (Danbooru standard).

Problem: Recent migration converted underscore → space (wrong direction)
- Danbooru standard: brown_hair, looking_at_viewer
- Current DB: mixed space/underscore

Solution:
1. Convert all space-format tags → underscore
2. Merge duplicates (space → underscore)
3. Delete space-format duplicates
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from database import SessionLocal
from models.tag import Tag, TagEffectiveness


def find_duplicate_pairs(db):
    """Find all duplicate tag pairs (space vs underscore).

    Returns:
        List of tuples: (underscore_tag, space_tag, underscore_id, space_id)
    """
    # Get all tags
    all_tags = db.query(Tag.id, Tag.name).all()

    # Build underscore → space mapping
    underscore_map = {}  # "brown_hair" → tag_id
    space_map = {}  # "brown hair" → tag_id

    for tag_id, name in all_tags:
        if "_" in name and " " not in name:
            underscore_map[name] = tag_id
        elif " " in name:
            space_map[name] = tag_id

    # Find pairs
    pairs = []
    for space_name, space_id in space_map.items():
        underscore_name = space_name.replace(" ", "_")
        if underscore_name in underscore_map:
            underscore_id = underscore_map[underscore_name]
            pairs.append((underscore_name, space_name, underscore_id, space_id))

    return pairs


def merge_effectiveness(db, underscore_id: int, space_id: int):
    """Merge effectiveness data from space to underscore tag."""
    underscore_eff = db.query(TagEffectiveness).filter(TagEffectiveness.tag_id == underscore_id).first()

    space_eff = db.query(TagEffectiveness).filter(TagEffectiveness.tag_id == space_id).first()

    if not space_eff:
        return "no space data"

    if not underscore_eff:
        # Transfer ownership
        space_eff.tag_id = underscore_id
        return "transferred"

    # Merge data
    underscore_eff.use_count += space_eff.use_count
    underscore_eff.match_count += space_eff.match_count
    underscore_eff.total_confidence += space_eff.total_confidence

    # Recalculate effectiveness
    if underscore_eff.use_count > 0:
        underscore_eff.effectiveness = underscore_eff.match_count / underscore_eff.use_count

    # Delete space record
    db.delete(space_eff)

    return f"merged ({space_eff.use_count} uses)"


def update_foreign_keys(db, underscore_id: int, space_id: int):
    """Update foreign key references from space to underscore."""
    # synonyms.tag_id
    db.execute(
        text("UPDATE synonyms SET tag_id = :underscore WHERE tag_id = :space"),
        {"underscore": underscore_id, "space": space_id},
    )

    # tag_rules.source_tag_id
    db.execute(
        text("UPDATE tag_rules SET source_tag_id = :underscore WHERE source_tag_id = :space"),
        {"underscore": underscore_id, "space": space_id},
    )

    # tag_rules.target_tag_id
    db.execute(
        text("UPDATE tag_rules SET target_tag_id = :underscore WHERE target_tag_id = :space"),
        {"underscore": underscore_id, "space": space_id},
    )

    # Integer arrays in characters table
    db.execute(
        text("""
            UPDATE characters
            SET identity_tags = array_replace(identity_tags, :space, :underscore)
            WHERE :space = ANY(identity_tags)
        """),
        {"underscore": underscore_id, "space": space_id},
    )

    db.execute(
        text("""
            UPDATE characters
            SET clothing_tags = array_replace(clothing_tags, :space, :underscore)
            WHERE :space = ANY(clothing_tags)
        """),
        {"underscore": underscore_id, "space": space_id},
    )


def convert_remaining_space_tags(db):
    """Convert remaining space-format tags (no duplicate) to underscore."""
    space_tags = db.query(Tag).filter(Tag.name.like("% %")).all()
    converted = []

    for tag in space_tags:
        underscore_name = tag.name.replace(" ", "_")
        # Check if underscore version already exists
        existing = db.query(Tag).filter(Tag.name == underscore_name).first()
        if existing:
            # Skip - will be handled by merge
            continue

        tag.name = underscore_name
        converted.append(f"{tag.name} (was: {tag.name.replace('_', ' ')})")

    return converted


def main():
    db = SessionLocal()

    try:
        print("Step 1: Finding duplicate pairs (space vs underscore)...")
        pairs = find_duplicate_pairs(db)
        print(f"Found {len(pairs)} duplicate pairs\n")

        if pairs:
            print("Preview (first 5):")
            for underscore_name, space_name, underscore_id, space_id in pairs[:5]:
                print(f"  '{underscore_name}' (ID {underscore_id}) ← '{space_name}' (ID {space_id})")
            print()

            print(f"Step 2: Merging {len(pairs)} duplicate pairs...")
            for underscore_name, space_name, underscore_id, space_id in pairs:
                # Merge effectiveness
                eff_result = merge_effectiveness(db, underscore_id, space_id)

                # Update foreign keys
                update_foreign_keys(db, underscore_id, space_id)

                # Delete space tag
                space_tag = db.query(Tag).filter(Tag.id == space_id).first()
                if space_tag:
                    db.delete(space_tag)

                print(f"✓ '{underscore_name}' ← '{space_name}' ({eff_result})")

            db.commit()

        print("\nStep 3: Converting remaining space-format tags...")
        converted = convert_remaining_space_tags(db)
        if converted:
            for entry in converted[:10]:
                print(f"  ✓ {entry}")
            if len(converted) > 10:
                print(f"  ... and {len(converted) - 10} more")
            db.commit()
            print(f"✅ Converted {len(converted)} tags to underscore format")
        else:
            print("  (No remaining space-format tags)")

        print("\n✅ Migration complete!")
        print(f"  - Merged: {len(pairs)} duplicate pairs")
        print(f"  - Converted: {len(converted)} remaining tags")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
