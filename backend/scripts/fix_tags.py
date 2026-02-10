"""Fix tag classification and migrate patterns safely."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from database import SessionLocal
from models.tag import ClassificationRule, Tag
from services.keywords import CATEGORY_PATTERNS


def migrate_patterns_safely(db):
    """Migrate patterns without relying on DB constraints yet."""
    count = 0
    for group_name, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            pattern = pattern.lower()
            # Check if exists
            exists = db.execute(
                select(ClassificationRule).where(
                    ClassificationRule.rule_type == "exact", ClassificationRule.pattern == pattern
                )
            ).scalar_one_or_none()

            if not exists:
                rule = ClassificationRule(
                    rule_type="exact", pattern=pattern, target_group=group_name, priority=0, is_active=True
                )
                db.add(rule)
                count += 1

    db.commit()
    print(f"✅ Migrated {count} patterns to rules.")
    return count


def classify_existing_tags(db):
    """Classify tags that have no category or group_name."""
    # Load rules
    rules = db.execute(select(ClassificationRule).where(ClassificationRule.is_active)).scalars().all()

    # Map rules for fast lookup
    exact_rules = {r.pattern: r.target_group for r in rules if r.rule_type == "exact"}

    # Get tags needing classification
    tags = db.execute(select(Tag).where(Tag.group_name is None)).scalars().all()

    print(f"🔍 Found {len(tags)} tags needing classification.")

    updated = 0
    for tag in tags:
        normalized = tag.name.lower().replace("_", " ").strip()

        # Try exact match
        group = exact_rules.get(normalized)

        if group:
            tag.group_name = group
            tag.classification_source = "rule"
            tag.classification_confidence = 0.95

            # Update category
            if group in [
                "identity",
                "hair_color",
                "hair_length",
                "hair_style",
                "hair_accessory",
                "eye_color",
                "skin_color",
                "body_feature",
                "appearance",
                "clothing",
            ]:
                tag.category = "character"
            elif group in ["quality", "style"]:
                tag.category = "meta"
            else:
                tag.category = "scene"

            updated += 1

        if updated % 1000 == 0 and updated > 0:
            db.commit()
            print(f"   Progress: {updated} tags updated...")

    db.commit()
    print(f"✅ Classified {updated} tags.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        migrate_patterns_safely(db)
        classify_existing_tags(db)
    finally:
        db.close()
