
from config import logger
from database import SessionLocal
from models import Tag


def fix_tag_categories():
    db = SessionLocal()
    try:
        # (name, target_category, target_group)
        tag_corrections = [
            ("holding_flower", "action", "action"),
            ("blush", "expression", "expression"),
            ("open_mouth", "expression", "expression"),
            ("smile", "expression", "expression"),
            ("outdoors", "location_outdoor", "location_outdoor"),
            ("sun", "time_weather", "time_weather"),
            ("beckoning", "pose", "pose"),
            ("standing", "pose", "pose"),
            ("full_body", "camera", "camera"),
            ("upper_body", "camera", "camera"),
        ]

        count = 0
        for name, category, group in tag_corrections:
            tag = db.query(Tag).filter(Tag.name == name).first()
            if tag:
                if tag.category != category or tag.group_name != group:
                    logger.info(f"Correcting {name}: {tag.category}/{tag.group_name} -> {category}/{group}")
                    tag.category = category
                    tag.group_name = group
                    tag.classification_confidence = 1.0
                    count += 1
            else:
                logger.info(f"Creating missing tag: {name} -> {category}/{group}")
                new_tag = Tag(
                    name=name,
                    category=category,
                    group_name=group,
                    classification_source="manual_fix",
                    classification_confidence=1.0
                )
                db.add(new_tag)
                count += 1

        db.commit()
        logger.info(f"✅ {count} tags corrected in database.")
    except Exception as e:
        logger.error(f"❌ Failed to correct tags: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_tag_categories()
