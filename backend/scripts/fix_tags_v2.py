"""Fix tag classification and migrate patterns comprehensively."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from database import SessionLocal
from models.tag import ClassificationRule, Tag
from services.keywords.patterns import CATEGORY_PATTERNS, suggest_category_for_tag


def migrate_patterns_to_rules(db):
    """Migrate all patterns to ClassificationRule table."""
    count = 0
    for group_name, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            pattern = pattern.lower().replace(" ", "_")
            # Check if exists
            exists = db.execute(
                select(ClassificationRule).where(
                    ClassificationRule.rule_type == "exact",
                    ClassificationRule.pattern == pattern
                )
            ).scalar_one_or_none()

            if not exists:
                rule = ClassificationRule(
                    rule_type="exact",
                    pattern=pattern,
                    target_group=group_name,
                    priority=0,
                    is_active=True
                )
                db.add(rule)
                count += 1

    db.commit()
    print(f"✅ Migrated {count} patterns to rules.")

def classify_tags_comprehensively(db):
    """Classify tags using the suggestion engine and assign default categories."""

    CHARACTER_GROUPS = {
        "identity", "hair_color", "hair_length", "hair_style", "hair_accessory",
        "eye_color", "skin_color", "body_feature", "appearance", "clothing"
    }
    META_GROUPS = {"quality", "style"}

    # Get all tags
    tags = db.execute(select(Tag)).scalars().all()
    print(f"🔍 Processing {len(tags)} tags...")

    updated = 0
    assigned_groups = 0

    for tag in tags:
        # 1. Use suggest_category_for_tag logic
        group, confidence = suggest_category_for_tag(tag.name)

        # 2. Assign group and category
        if group:
            tag.group_name = group
            tag.classification_confidence = confidence
            tag.classification_source = "rule"
            assigned_groups += 1

            if group in CHARACTER_GROUPS:
                tag.category = "character"
            elif group in META_GROUPS:
                tag.category = "meta"
            else:
                tag.category = "scene"
        else:
            # Default fallback for tags that don't match any rule
            # If it's currently null, we at least give it a category to show up in "Tag Analysis"
            if tag.category is None:
                tag.category = "scene" # Default category
                tag.group_name = "subject" # Default group for unknown descriptive tags
                tag.classification_source = "default"
                tag.classification_confidence = 0.5

        updated += 1
        if updated % 2000 == 0:
            db.commit()
            print(f"   Progress: {updated} tags processed...")

    db.commit()
    print(f"✅ Finished! Updated {updated} tags. Assigned specific groups to {assigned_groups} tags.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        migrate_patterns_to_rules(db)
        classify_tags_comprehensively(db)
    finally:
        db.close()
