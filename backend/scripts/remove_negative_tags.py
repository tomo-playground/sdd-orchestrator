"""Remove problematic tags from character negative prompts.

Removes: cropped, head out of frame, out of frame
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models.character import Character

TAGS_TO_REMOVE = ["cropped", "head out of frame", "out of frame"]


def main():
    db = SessionLocal()
    try:
        # Get all characters with negative prompts
        characters = db.query(Character).filter(
            Character.recommended_negative.isnot(None)
        ).all()

        print(f"Found {len(characters)} characters with negative prompts")
        print()

        updated_count = 0
        for char in characters:
            original = char.recommended_negative.copy() if char.recommended_negative else []

            # Remove problematic tags
            char.recommended_negative = [
                tag for tag in char.recommended_negative
                if tag not in TAGS_TO_REMOVE
            ]

            # Check if anything changed
            if char.recommended_negative != original:
                removed = set(original) - set(char.recommended_negative)
                print(f"✓ {char.name}")
                print(f"  Removed: {sorted(removed)}")
                print(f"  Before ({len(original)} tags): {original}")
                print(f"  After ({len(char.recommended_negative)} tags): {char.recommended_negative}")
                print()
                updated_count += 1

        if updated_count > 0:
            db.commit()
            print(f"✅ Successfully updated {updated_count} characters")
        else:
            print("No changes needed")

    except Exception as exc:
        db.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
