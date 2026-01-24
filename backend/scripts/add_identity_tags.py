#!/usr/bin/env python3
"""Add Danbooru-based Identity tags to database.

Usage:
    cd backend && uv run python scripts/add_identity_tags.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Tag

# Identity tags based on Danbooru standards
IDENTITY_TAGS = {
    "hair_color": {
        "category": "character",
        "priority": 3,
        "exclusive": True,
        "tags": [
            "black_hair",
            "blonde_hair",
            "blue_hair",
            "brown_hair",
            "green_hair",
            "grey_hair",
            "orange_hair",
            "pink_hair",
            "purple_hair",
            "red_hair",
            "silver_hair",
            "white_hair",
            "aqua_hair",
            "light_brown_hair",
            "dark_blue_hair",
            "light_blue_hair",
            "light_purple_hair",
            "multicolored_hair",
            "two-tone_hair",
            "gradient_hair",
            "streaked_hair",
        ],
    },
    "eye_color": {
        "category": "character",
        "priority": 3,
        "exclusive": True,
        "tags": [
            "black_eyes",
            "blue_eyes",
            "brown_eyes",
            "green_eyes",
            "grey_eyes",
            "orange_eyes",
            "pink_eyes",
            "purple_eyes",
            "red_eyes",
            "yellow_eyes",
            "aqua_eyes",
            "heterochromia",
            "multicolored_eyes",
        ],
    },
    "hair_length": {
        "category": "character",
        "priority": 3,
        "exclusive": True,
        "tags": [
            "very_short_hair",
            "short_hair",
            "medium_hair",
            "long_hair",
            "very_long_hair",
            "absurdly_long_hair",
        ],
    },
    "hair_style": {
        "category": "character",
        "priority": 3,
        "exclusive": False,
        "tags": [
            "ahoge",
            "bangs",
            "blunt_bangs",
            "side_bangs",
            "parted_bangs",
            "asymmetrical_bangs",
            "hair_over_one_eye",
            "hair_over_eyes",
            "hair_between_eyes",
            "sidelocks",
            "ponytail",
            "side_ponytail",
            "low_ponytail",
            "high_ponytail",
            "twintails",
            "low_twintails",
            "short_twintails",
            "braid",
            "twin_braids",
            "side_braid",
            "french_braid",
            "hair_bun",
            "double_bun",
            "bob_cut",
            "pixie_cut",
            "hime_cut",
            "drill_hair",
            "twin_drills",
            "wavy_hair",
            "curly_hair",
            "straight_hair",
            "messy_hair",
            "hair_flaps",
            "hair_intakes",
        ],
    },
    "hair_accessory": {
        "category": "character",
        "priority": 4,
        "exclusive": False,
        "tags": [
            "hair_ornament",
            "hair_ribbon",
            "hair_bow",
            "hairband",
            "hairclip",
            "hair_flower",
            "hairpin",
            "x_hair_ornament",
            "star_hair_ornament",
            "heart_hair_ornament",
            "hair_tie",
            "scrunchie",
            "hair_bell",
        ],
    },
}


def add_identity_tags(db: Session) -> tuple[int, int]:
    """Add identity tags to database. Returns (added, skipped) count."""
    added = 0
    skipped = 0

    for group_name, config in IDENTITY_TAGS.items():
        for tag_name in config["tags"]:
            # Check if already exists
            existing = db.query(Tag).filter(Tag.name == tag_name).first()
            if existing:
                skipped += 1
                continue

            tag = Tag(
                name=tag_name,
                category=config["category"],
                group_name=group_name,
                priority=config["priority"],
                exclusive=config["exclusive"],
            )
            db.add(tag)
            added += 1

    return added, skipped


def main():
    """Main function."""
    print("🚀 Adding Danbooru Identity tags...")

    db = SessionLocal()
    try:
        added, skipped = add_identity_tags(db)
        db.commit()
        print(f"  ✅ Added {added} new tags")
        print(f"  ⏭️  Skipped {skipped} existing tags")
        print("🎉 Done!")
    except Exception as e:
        db.rollback()
        print(f"❌ Failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
