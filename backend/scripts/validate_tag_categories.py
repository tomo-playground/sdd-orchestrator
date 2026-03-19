"""
DB Tag Category Validation Script

This script validates that all tags in the database have appropriate categories
and identifies potential misclassifications.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict

from database import SessionLocal
from models import Tag

# Expected categories and their typical patterns
CATEGORY_PATTERNS = {
    "expression": ["smiling", "crying", "laughing", "happy", "sad", "angry", "surprised", "neutral"],
    "gaze": ["looking_at_viewer", "looking_away", "looking_down", "looking_up", "closed_eyes", "eye_contact"],
    "pose": ["standing", "sitting", "lying", "kneeling", "crouching", "squatting"],
    "action": ["waving", "pointing", "stretching", "running", "walking", "jumping"],
    "camera": ["upper_body", "full_body", "cowboy_shot", "close-up", "from_above", "from_below"],
    "subject": ["1girl", "1boy", "2girls", "2boys", "solo", "multiple_girls"],
    "hair_length": ["short_hair", "long_hair", "medium_hair", "very_long_hair"],
    "hair_color": ["black_hair", "brown_hair", "blonde_hair", "red_hair", "blue_hair", "green_hair", "pink_hair"],
    "eye_color": ["blue_eyes", "brown_eyes", "green_eyes", "red_eyes", "purple_eyes"],
    "clothing": ["school_uniform", "dress", "shirt", "skirt", "pants", "jacket"],
    "location_indoor": ["bedroom", "classroom", "kitchen", "bathroom", "office", "library"],
    "location_outdoor": ["park", "street", "beach", "forest", "mountain", "city"],
    "time_weather": ["day", "night", "sunset", "sunrise", "rain", "snow", "cloudy"],
    "lighting": ["bright", "dark", "dramatic_lighting", "soft_lighting", "backlight"],
    "quality": ["best_quality", "high_quality", "normal_quality", "low_quality"],
    "meta": ["masterpiece", "official_art", "highres", "lowres"],
    "style": ["anime_style", "realistic", "cartoon", "chibi"],
}

# Categories that should NOT map to location_indoor/outdoor
NON_LOCATION_CATEGORIES = {
    "expression",
    "gaze",
    "pose",
    "action",
    "camera",
    "subject",
    "hair_length",
    "hair_color",
    "eye_color",
    "clothing",
    "quality",
    "meta",
    "style",
}


def validate_tag_categories():
    db = SessionLocal()
    try:
        print("\n" + "=" * 80)
        print("TAG CATEGORY VALIDATION REPORT")
        print("=" * 80 + "\n")

        # 1. Category distribution
        print("📊 CATEGORY DISTRIBUTION")
        print("-" * 80)
        category_counts = defaultdict(int)
        tags = db.query(Tag).all()

        for tag in tags:
            category_counts[tag.category or "NULL"] += 1

        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"  {category:20} : {count:5} tags")

        print(f"\n  Total tags: {len(tags)}")

        # 2. Find tags that might be miscategorized
        print("\n\n⚠️  POTENTIAL MISCLASSIFICATIONS")
        print("-" * 80)

        issues_found = 0
        for tag in tags:
            tag_name = tag.name.lower()

            # Check if tag name suggests a different category
            for expected_cat, patterns in CATEGORY_PATTERNS.items():
                if any(pattern in tag_name for pattern in patterns):
                    if tag.category != expected_cat:
                        # Special case: scene can have subcategories
                        if tag.category == "scene" and expected_cat in [
                            "location_indoor",
                            "location_outdoor",
                            "time_weather",
                        ]:
                            continue

                        print(f"  {tag.name:30} -> {tag.category or 'NULL':20} (expected: {expected_cat})")
                        issues_found += 1
                        break

        if issues_found == 0:
            print("  ✅ No obvious misclassifications found")
        else:
            print(f"\n  Found {issues_found} potential issues")

        # 3. Check for tags mapped to location_indoor/outdoor that shouldn't be
        print("\n\n🔍 CHECKING FOR INCORRECT LOCATION MAPPINGS")
        print("-" * 80)

        from services.keywords.db_cache import TagCategoryCache

        TagCategoryCache.initialize(db)

        incorrect_mappings = []
        for tag in tags:
            prompt_category = TagCategoryCache.get_category(tag.name)

            if prompt_category in ["location_indoor", "location_outdoor"]:
                # Check if this tag should be in a non-location category
                for expected_cat in NON_LOCATION_CATEGORIES:
                    if expected_cat in CATEGORY_PATTERNS:
                        if any(pattern in tag.name.lower() for pattern in CATEGORY_PATTERNS[expected_cat]):
                            incorrect_mappings.append((tag.name, tag.category, prompt_category, expected_cat))
                            break

        if incorrect_mappings:
            print(f"  Found {len(incorrect_mappings)} tags incorrectly mapped to location categories:\n")
            for name, db_cat, prompt_cat, expected_cat in incorrect_mappings[:20]:  # Show first 20
                print(f"  {name:30} (DB: {db_cat:15}) -> {prompt_cat:20} (should be: {expected_cat})")

            if len(incorrect_mappings) > 20:
                print(f"\n  ... and {len(incorrect_mappings) - 20} more")
        else:
            print("  ✅ No incorrect location mappings found")

        # 4. Tags without categories
        print("\n\n❓ TAGS WITHOUT CATEGORIES")
        print("-" * 80)

        no_category = [tag for tag in tags if not tag.category]
        if no_category:
            print(f"  Found {len(no_category)} tags without categories")
            for tag in no_category[:10]:
                print(f"  - {tag.name}")
            if len(no_category) > 10:
                print(f"  ... and {len(no_category) - 10} more")
        else:
            print("  ✅ All tags have categories")

        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    validate_tag_categories()
