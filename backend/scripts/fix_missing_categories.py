from database import SessionLocal
from models.tag import Tag


def fix_categories():
    db = SessionLocal()

    # Map of category -> list of tags
    # Based on what user showed as "Other"
    updates = {
        "quality": ["best_quality", "high_quality", "masterpiece", "amazing_quality"],
        "style": ["anime_style", "cute_anime_style", "chibi"],
        "gaze": ["looking_at_viewer", "looking_away"],
        "camera": ["upper_body", "full_body", "close_up"],
        "hair_length": ["long_hair", "short_hair"],
        "action": ["thinking", "holding_flower"],
        "time_weather": ["day", "night", "sunlight", "outdoors", "indoors"], # outdoors/indoors sometimes map to location
        "subject": ["1girl", "1boy"],
        "expression": ["happy", "smile"],
    }

    try:
        count = 0
        for category, tags in updates.items():
            for tag_name in tags:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if tag:
                    # Update category if different
                    if tag.category != category:
                        print(f"Updating {tag_name}: category {tag.category} -> {category}")
                        tag.category = category
                        count += 1

                    # Update group_name if missing or different (assume group_name ~= category for these basic tags)
                    # For hair_length, category is 'hair_length', group should also be 'hair_length'
                    if tag.group_name != category:
                         print(f"Updating {tag_name}: group {tag.group_name} -> {category}")
                         tag.group_name = category
                         # Mark as manually classified so it sticks
                         tag.classification_source = "manual"
                         tag.classification_confidence = 1.0
                         count += 1
                else:
                    # Create if not exists
                    print(f"Creating {tag_name} as {category}")
                    # classification_source='manual' ensures it's treated as a confirmed classification
                    tag = Tag(
                        name=tag_name,
                        category=category,
                        group_name=category,
                        classification_source="manual",
                        classification_confidence=1.0
                    )
                    db.add(tag)
                    count += 1

        db.commit()
        print(f"✅ Updated {count} tags.")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_categories()
