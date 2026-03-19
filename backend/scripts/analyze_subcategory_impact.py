#!/usr/bin/env python3
"""[DEPRECATED] Subcategory Impact Analysis Script

NOTE: subcategory field was deprecated and all values set to NULL (Phase 6-4.25, 2026-01-30).
The prompt composition system now relies solely on group_name for semantic classification.
Kept for historical reference only.

Original Purpose: Analyzed the impact of subcategory field on prompt composition quality.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import SessionLocal
from models.tag import Tag

# Import mapping directly to avoid service dependencies
SUBCATEGORY_TO_PROMPT = {
    "indoor": "location_indoor",
    "outdoor": "location_outdoor",
    "time": "time_weather",
    "clothing": "clothing",
}


def main():
    db = SessionLocal()

    print("=" * 80)
    print("SUBCATEGORY FIELD IMPACT ANALYSIS")
    print("=" * 80)

    # 1. Basic Stats
    total_tags = db.query(Tag).count()
    tags_with_subcategory = db.query(Tag).filter(Tag.subcategory.isnot(None), Tag.subcategory != "").count()

    print("\n📊 Basic Statistics:")
    print(f"  Total Tags:              {total_tags:,}")
    print(f"  Tags with subcategory:   {tags_with_subcategory:,} ({tags_with_subcategory / total_tags * 100:.1f}%)")

    # 2. Subcategory Distribution
    print("\n📈 Subcategory Distribution:")
    from sqlalchemy import text

    result = db.execute(
        text("""
        SELECT subcategory, COUNT(*) as cnt
        FROM tags
        WHERE subcategory IS NOT NULL AND subcategory != ''
        GROUP BY subcategory
        ORDER BY cnt DESC
    """)
    )

    for row in result:
        subcategory, count = row
        prompt_cat = SUBCATEGORY_TO_PROMPT.get(subcategory, "❌ UNMAPPED")
        print(f"  {subcategory:15} → {prompt_cat:20} | {count:5} tags")

    # 3. Mismatch Analysis (subcategory vs group_name)
    print("\n⚠️  Mismatch Analysis (subcategory != group_name logic):")

    for subcategory, expected_prompt_cat in SUBCATEGORY_TO_PROMPT.items():
        # Find tags where subcategory suggests one category but group_name says another
        mismatches = (
            db.query(Tag)
            .filter(Tag.subcategory == subcategory, Tag.group_name.isnot(None), Tag.group_name != expected_prompt_cat)
            .all()
        )

        if mismatches:
            print(f"\n  subcategory='{subcategory}' → expects '{expected_prompt_cat}'")
            print(f"  But {len(mismatches)} tags have DIFFERENT group_name:")

            # Group by actual group_name
            from collections import defaultdict

            by_group = defaultdict(list)
            for tag in mismatches:
                by_group[tag.group_name].append(tag.name)

            for group_name, tags in sorted(by_group.items()):
                print(f"    group_name='{group_name}': {len(tags)} tags")
                # Show 5 examples
                for tag in tags[:5]:
                    print(f"      - {tag}")
                if len(tags) > 5:
                    print(f"      ... and {len(tags) - 5} more")

    # 4. Semantic Validation (check if subcategory makes sense)
    print("\n🔍 Semantic Validation (subcategory='indoor' but NOT location tag):")

    # Tags that have subcategory=indoor but are NOT actually location tags
    semantic_errors = (
        db.query(Tag)
        .filter(
            Tag.subcategory == "indoor",
            Tag.category != "scene",  # Not even scene category
        )
        .limit(20)
        .all()
    )

    if semantic_errors:
        print(f"  Found {len(semantic_errors)} tags marked 'indoor' but not scene/location:")
        for tag in semantic_errors:
            print(
                f"    {tag.name:25} | category={tag.category:15} | group={tag.group_name or 'NULL':20} | layer={tag.default_layer}"
            )

    # 5. Consistency Check (same tag, different subcategory?)
    print("\n🧐 Priority Logic Test:")
    print("  Current priority: subcategory > group_name (if granular) > category")

    # Find cases where subcategory and group_name both exist
    both_set = (
        db.query(Tag)
        .filter(Tag.subcategory.isnot(None), Tag.subcategory != "", Tag.group_name.isnot(None), Tag.group_name != "")
        .all()
    )

    consistent_count = 0
    inconsistent_count = 0
    inconsistent_examples = []

    for tag in both_set:
        expected = SUBCATEGORY_TO_PROMPT.get(tag.subcategory)
        if expected == tag.group_name:
            consistent_count += 1
        else:
            inconsistent_count += 1
            if len(inconsistent_examples) < 10:
                inconsistent_examples.append(
                    {
                        "tag": tag.name,
                        "subcategory": tag.subcategory,
                        "expected": expected,
                        "group_name": tag.group_name,
                    }
                )

    print(f"  Tags with both subcategory AND group_name set: {len(both_set)}")
    print(f"    ✅ Consistent (subcategory matches group_name): {consistent_count}")
    print(f"    ❌ Inconsistent (subcategory != group_name):    {inconsistent_count}")

    if inconsistent_examples:
        print("\n  Examples of inconsistent tags:")
        for ex in inconsistent_examples:
            print(
                f"    {ex['tag']:25} | subcategory={ex['subcategory']:10} → expects '{ex['expected']:20}' | actual group={ex['group_name']}"
            )

    # 6. Recommendation
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATION")
    print("=" * 80)

    if inconsistent_count > consistent_count:
        print(f"""
❌ REMOVE subcategory field

Reason:
  - {inconsistent_count}/{len(both_set)} tags have subcategory that CONTRADICTS group_name
  - Subcategory adds complexity without quality benefit
  - group_name is more accurate and granular

Action:
  1. Remove subcategory from priority logic (db_cache.py)
  2. Add migration to deprecate subcategory column
  3. Use group_name → category fallback only
""")
    else:
        print(f"""
✅ KEEP but FIX subcategory field

Reason:
  - {consistent_count}/{len(both_set)} tags have consistent subcategory
  - Field provides useful categorization hint

Action:
  1. Clean bad data (fix {inconsistent_count} mismatched tags)
  2. Add validation to prevent future mismatches
  3. Consider inverting priority: group_name > subcategory
""")

    db.close()


if __name__ == "__main__":
    main()
